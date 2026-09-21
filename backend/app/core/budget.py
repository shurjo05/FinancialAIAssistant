"""A per-day call budget for the LLM (single-instance, best-effort).

Per-minute rate limits cap burst abuse but not a slow drip; this is the hard
daily ceiling that guarantees Jo can never run up the Gemini bill. It counts
only *successful* Gemini calls per UTC day (check `has_budget()` before, then
`record()` after a call returns), so a Gemini outage or rate-limit — where the
call never produced an answer — doesn't waste the daily budget. Resets when the
day rolls over. In-memory (resets on restart), fine for a single instance.
"""

import datetime
import threading


class _DailyBudget:
    def __init__(self, limit_getter) -> None:
        self._lock = threading.Lock()
        self._limit_getter = limit_getter
        self._day: datetime.date | None = None
        self._count = 0

    def _roll(self, today: datetime.date) -> None:
        if self._day != today:
            self._day = today
            self._count = 0

    def has_budget(self) -> bool:
        """Whether today still has room (does NOT reserve — call record() on success)."""
        today = datetime.datetime.now(datetime.UTC).date()
        with self._lock:
            self._roll(today)
            return self._count < self._limit_getter()

    def record(self) -> None:
        """Count one successful call against today's budget."""
        today = datetime.datetime.now(datetime.UTC).date()
        with self._lock:
            self._roll(today)
            self._count += 1

    def try_consume(self) -> bool:
        """Reserve one call up front. Returns False if today's budget is spent."""
        today = datetime.datetime.now(datetime.UTC).date()
        with self._lock:
            self._roll(today)
            if self._count >= self._limit_getter():
                return False
            self._count += 1
            return True

    def status(self) -> dict:
        today = datetime.datetime.now(datetime.UTC).date()
        with self._lock:
            self._roll(today)
            limit = self._limit_getter()
            return {"used": self._count, "limit": limit, "remaining": max(0, limit - self._count)}


def _cap() -> int:
    from app.core.config import settings
    return settings.gemini_daily_cap


# Shared instance imported by the AI service.
gemini_budget = _DailyBudget(_cap)
