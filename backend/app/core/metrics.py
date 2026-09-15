"""In-memory application metrics (single-instance, best-effort).

A tiny thread-safe registry of counters + timing aggregates, exposed at
`GET /api/metrics`. Deliberately not Prometheus — appropriate for a
single-instance deploy. It resets on restart (documented), and never stores
financial values, only counts and latencies.
"""

import threading
from collections import defaultdict


class _Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "total_ms": 0.0, "last_ms": 0.0}
        )

    def incr(self, name: str, by: int = 1) -> None:
        with self._lock:
            self._counters[name] += by

    def observe_ms(self, name: str, ms: float) -> None:
        with self._lock:
            t = self._timers[name]
            t["count"] += 1
            t["total_ms"] += ms
            t["last_ms"] = ms

    def snapshot(self) -> dict:
        with self._lock:
            timers = {
                k: {
                    "count": v["count"],
                    "avg_ms": round(v["total_ms"] / v["count"], 1) if v["count"] else 0.0,
                    "last_ms": round(v["last_ms"], 1),
                }
                for k, v in self._timers.items()
            }
            return {"counters": dict(self._counters), "timers": timers}


# Single shared registry imported across the app.
metrics = _Metrics()
