"""AI query layer: answer natural-language questions grounded in the data.

Dispatches to a provider chain:
    Gemini (if GOOGLE_API_KEY set)  ->  deterministic rule-based fallback.

Every provider answers using the same data tools in app/services/tools.py, so
answers are always computed from the database, never hallucinated. The
rule-based fallback means the feature works with zero API keys.
"""

import calendar
import re

from sqlalchemy.orm import Session

from app.core.budget import gemini_budget
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import metrics
from app.services import tools
from app.services.categorizer import CATEGORIES

logger = get_logger("app.ai")


class AIUnavailable(Exception):
    """Gemini was expected (an API key is configured) but temporarily failed.

    Raised instead of silently answering from the deterministic engine, because
    a context-less rule-based reply to a conversational follow-up is worse than
    telling the user to retry. The endpoints surface this as a 503 the chat UI
    renders with a Retry button. `reason` is for logs/metrics; `message` is shown.
    """

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        self.message = message
        super().__init__(message)


# User-facing copy per failure reason (all transient / retryable).
_UNAVAILABLE_MESSAGES = {
    "rate_limited": "Jo's getting a lot of requests right now — give it a few seconds and hit retry.",
    "unavailable": "Jo's AI service is momentarily unavailable. Please retry.",
    "timeout": "That took too long to answer. Please retry.",
    "budget": "Jo has reached today's AI usage limit. Please try again later.",
    "error": "Jo hit a snag answering that. Please retry.",
}


def _classify_llm_error(exc: Exception) -> str:
    """Bucket a Gemini failure so we log *why* we fell back (not just that we did)."""
    msg = str(exc).lower()
    if any(s in msg for s in ("429", "resource_exhausted", "quota", "rate")):
        return "rate_limited"
    if any(s in msg for s in ("503", "unavailable", "overloaded")):
        return "unavailable"
    if any(s in msg for s in ("timeout", "deadline")):
        return "timeout"
    return "error"

_MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})

# Everyday words mapped to our display categories, for the fallback parser.
_CATEGORY_SYNONYMS = {
    "food": "restaurants", "dining": "restaurants", "eating out": "restaurants",
    "restaurant": "restaurants", "grocery": "groceries", "gas": "transport",
    "fuel": "transport", "housing": "rent", "streaming": "subscriptions",
    "medical": "health", "doctor": "health",
}


def _detect_category(text: str) -> str | None:
    for category in CATEGORIES:
        if category in text:
            return category
    for word, category in _CATEGORY_SYNONYMS.items():
        if word in text:
            return category
    return None


def _detect_month(text: str, year: int) -> str | None:
    for name, num in _MONTHS.items():
        if re.search(rf"\b{name}\b", text):
            return f"{year}-{num:02d}"
    return None


def fallback_answer(db: Session, user_id: int, question: str) -> tuple[str, list[str]]:
    """Deterministic keyword-based answer. Returns (answer_text, tools_used)."""
    q = question.lower()
    rng = tools.date_range(db, user_id)
    year = int(rng["start"][:4]) if rng["start"] else 2024

    if "bill" in q or "recurring payment" in q:
        d = tools.list_recurring_bills(db, user_id)
        return (
            f"You have {d['count']} recurring bills totaling "
            f"${d['monthly_cost']:,.2f}/month (${d['annual_cost']:,.2f}/year).",
            ["list_recurring_bills"],
        )

    if "subscription" in q or "recurring" in q:
        d = tools.list_subscriptions(db, user_id)
        return (
            f"You have {d['count']} subscriptions totaling "
            f"${d['monthly_cost']:,.2f}/month (${d['annual_cost']:,.2f}/year).",
            ["list_subscriptions"],
        )

    if any(w in q for w in ("anomal", "unusual", "weird", "suspicious", "spike")):
        d = tools.list_anomalies(db, user_id)
        if not d["count"]:
            return ("I didn't find any unusual transactions.", ["list_anomalies"])
        top = d["anomalies"][0]["description"]
        return (f"I found {d['count']} unusual transactions. The biggest: {top}.",
                ["list_anomalies"])

    if "top" in q and "merchant" in q:
        d = tools.top_merchants(db, user_id, n=5)
        listing = "; ".join(f"{m['merchant']} (${m['total']:,.2f})" for m in d["merchants"])
        return (f"Your top merchants by spend: {listing}.", ["top_merchants"])

    month = _detect_month(q, year)
    category = _detect_category(q)
    start = end = None
    month_label = ""
    if month:
        lo, hi = tools.month_bounds(month)
        start, end, month_label = lo.isoformat(), hi.isoformat(), f" in {calendar.month_name[int(month[5:7])]}"

    if any(w in q for w in ("income", "earn", "made", "paid", "salary")):
        d = tools.get_total(db, user_id, "income", start, end)
        return (f"Your total income{month_label} was ${d['total']:,.2f}.", ["get_total"])

    if category:
        d = tools.get_spending_by_category(db, user_id, category, start, end)
        return (f"You spent ${d['total']:,.2f} on {category}{month_label} "
                f"across {d['count']} transactions.", ["get_spending_by_category"])

    d = tools.get_total(db, user_id, "spending", start, end)
    return (f"Your total spending{month_label} was ${d['total']:,.2f}.", ["get_total"])


def answer_query(
    db: Session,
    user_id: int,
    question: str,
    history: list[dict] | None = None,
    style: str = "friendly",
) -> dict:
    """Answer a question for one user.

    Marker for whether we ever fall back: **is an API key configured?**
      - No key  → offline / zero-keys mode; the deterministic engine IS the
        answer (the app's no-API-key guarantee). This is the only path that
        returns a rule-based answer to a user.
      - Key set → Gemini is expected. Any failure (rate limit, outage, timeout,
        or the daily budget cap) raises `AIUnavailable` (a retryable 503) rather
        than silently degrading to a context-less rule-based reply — which, with
        conversation memory in play, would usually be wrong.

    `history` is the bounded conversation-memory window (may be empty).
    """
    metrics.incr("query_total")

    if not settings.google_api_key:
        answer, tools_used = fallback_answer(db, user_id, question)
        metrics.incr("query_rulebased_total")
        return {"answer": answer, "provider": "rule-based", "tools_used": tools_used}

    # A key is configured: Gemini is the expected answer path. Check the daily
    # budget WITHOUT reserving, and only count the call if it actually succeeds —
    # so an outage / rate-limit (which produced no answer) never wastes budget.
    if not gemini_budget.has_budget():
        metrics.incr("query_unavailable_total")
        metrics.incr("query_unavailable_budget")
        logger.warning("gemini daily budget spent")
        raise AIUnavailable("budget", _UNAVAILABLE_MESSAGES["budget"])

    try:
        from app.services.gemini_provider import gemini_answer
        result = gemini_answer(db, user_id, question, history=history, style=style)
        gemini_budget.record()  # count only a successful call
        metrics.incr("query_gemini_total")
        return result
    except Exception as exc:
        # Classify + log WHY (rate limit vs error) without logging the question.
        reason = _classify_llm_error(exc)
        metrics.incr("query_unavailable_total")
        metrics.incr(f"query_unavailable_{reason}")
        logger.warning(
            "gemini query failed; surfacing retryable error",
            extra={"reason": reason, "error_type": type(exc).__name__},
        )
        raise AIUnavailable(reason, _UNAVAILABLE_MESSAGES.get(reason, _UNAVAILABLE_MESSAGES["error"])) from exc
