"""Gemini provider: answers questions via automatic function-calling.

We expose the data tools as Python callables (closed over the DB session). The
google-genai SDK reads their signatures + docstrings to build function
declarations, lets the model decide which to call, executes them, and returns a
grounded natural-language answer. Any failure here is caught by ai_service,
which falls back to the deterministic engine.
"""

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import tools

SYSTEM_INSTRUCTION = (
    "You are a personal finance analyst. Answer the user's question using ONLY "
    "the provided tools to fetch real numbers from their transaction data. "
    "Never invent figures. Be concise and specific, and format money as US "
    "dollars. Transaction data covers the date range {start} to {end}; resolve "
    "relative months (e.g. 'March') to that range's year."
)


def _make_tools(db: Session, user_id: int) -> list:
    """Build LLM-facing tool callables bound to this DB session and user.

    Signatures use simple typed args with defaults so the SDK can introspect
    them; docstrings become the tool descriptions the model reads. Every tool is
    scoped to `user_id`, so the model can only ever read this user's data.
    """

    def get_spending_by_category(category: str = "", start_date: str = "", end_date: str = "") -> dict:
        """Total spending, optionally filtered to one category and/or a date range (YYYY-MM-DD)."""
        return tools.get_spending_by_category(db, user_id, category or None, start_date or None, end_date or None)

    def get_total(kind: str = "spending", start_date: str = "", end_date: str = "") -> dict:
        """Total 'spending' (money out) or 'income' (money in) over an optional date range."""
        return tools.get_total(db, user_id, kind, start_date or None, end_date or None)

    def top_merchants(n: int = 5, start_date: str = "", end_date: str = "") -> dict:
        """The top N merchants by total spend over an optional date range."""
        return tools.top_merchants(db, user_id, n, start_date or None, end_date or None)

    def compare_periods(period_a: str, period_b: str, category: str = "") -> dict:
        """Compare spending between two months (YYYY-MM), optionally for one category."""
        return tools.compare_periods(db, user_id, period_a, period_b, category or None)

    def list_subscriptions() -> dict:
        """List discretionary subscriptions (streaming, gym, software) with monthly/annual cost."""
        return tools.list_subscriptions(db, user_id)

    def list_recurring_bills() -> dict:
        """List essential recurring bills (rent, utilities, insurance) with monthly/annual cost."""
        return tools.list_recurring_bills(db, user_id)

    def list_anomalies() -> dict:
        """List flagged unusual/anomalous transactions."""
        return tools.list_anomalies(db, user_id)

    return [get_spending_by_category, get_total, top_merchants, compare_periods,
            list_subscriptions, list_recurring_bills, list_anomalies]


def gemini_answer(db: Session, user_id: int, question: str) -> dict:
    """Answer via Gemini with automatic function-calling, scoped to one user."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.google_api_key)
    rng = tools.date_range(db, user_id)

    config = types.GenerateContentConfig(
        tools=_make_tools(db, user_id),
        system_instruction=SYSTEM_INSTRUCTION.format(start=rng["start"], end=rng["end"]),
    )
    response = client.models.generate_content(
        model=settings.google_model,
        contents=question,
        config=config,
    )

    # Recover which tools the model actually called, for transparency.
    tools_used: list[str] = []
    for content in (getattr(response, "automatic_function_calling_history", None) or []):
        for part in (getattr(content, "parts", None) or []):
            fc = getattr(part, "function_call", None)
            if fc and fc.name:
                tools_used.append(fc.name)

    return {
        "answer": response.text,
        "provider": "gemini",
        "tools_used": list(dict.fromkeys(tools_used)),  # de-dupe, keep order
    }
