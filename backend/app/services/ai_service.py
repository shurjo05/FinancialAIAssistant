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

from app.core.config import settings
from app.services import tools
from app.services.categorizer import CATEGORIES

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


def answer_query(db: Session, user_id: int, question: str) -> dict:
    """Answer a question for one user, preferring Gemini and falling back to rules."""
    if settings.google_api_key:
        try:
            from app.services.gemini_provider import gemini_answer
            return gemini_answer(db, user_id, question)
        except Exception:
            pass  # any Gemini failure -> deterministic fallback

    answer, tools_used = fallback_answer(db, user_id, question)
    return {"answer": answer, "provider": "rule-based", "tools_used": tools_used}
