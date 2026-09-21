"""Phase 13: observability, gzip, and agent-loop hardening."""

from app.core.metrics import metrics
from app.services import tools
from app.services.ai_service import _classify_llm_error, answer_query


def test_health_reports_db(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_metrics_endpoint_shape(client):
    client.get("/api/health")  # generate some traffic
    m = client.get("/api/metrics").json()
    assert "counters" in m and "timers" in m
    assert m["counters"]["http_requests_total"] >= 1


def test_large_response_is_gzipped(auth_client):
    auth_client.post("/api/load-sample")
    r = auth_client.get(
        "/api/transactions",
        params={"page_size": 100},
        headers={"Accept-Encoding": "gzip"},
    )
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"


def test_compare_periods_returns_structured_error(db, user):
    out = tools.compare_periods(db, user.id, "not-a-month", "2024-03")
    assert "error" in out  # structured error, not a raised exception


def test_get_total_clamps_unknown_kind(db, user):
    # Unknown kind must not raise; it clamps to 'spending'.
    out = tools.get_total(db, user.id, kind="nonsense")
    assert out["kind"] == "spending"


def test_classify_llm_error():
    assert _classify_llm_error(Exception("429 RESOURCE_EXHAUSTED")) == "rate_limited"
    assert _classify_llm_error(Exception("503 Service Unavailable")) == "unavailable"
    assert _classify_llm_error(Exception("deadline exceeded")) == "timeout"
    assert _classify_llm_error(Exception("boom")) == "error"


def test_gemini_failure_raises_retryable_with_logged_reason(db, user, monkeypatch):
    """A Gemini failure (key configured) surfaces a retryable error, classified + counted.

    Since Phase 21, a keyed deployment never silently degrades to a context-less
    rule-based answer; it raises AIUnavailable (a 503 the chat renders as Retry).
    """
    import pytest

    from app.core.config import settings
    from app.services import gemini_provider
    from app.services.ai_service import AIUnavailable

    monkeypatch.setattr(settings, "google_api_key", "test-key")

    def boom(*a, **k):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: quota")

    monkeypatch.setattr(gemini_provider, "gemini_answer", boom)

    before = metrics.snapshot()["counters"].get("query_unavailable_total", 0)
    with pytest.raises(AIUnavailable) as ei:
        answer_query(db, user.id, "how much did I spend?")
    after = metrics.snapshot()["counters"].get("query_unavailable_total", 0)

    assert ei.value.reason == "rate_limited"
    assert ei.value.message  # user-facing copy present
    assert after == before + 1
