"""Tests for Jo's conversation memory, persistence, guardrails and budget.

The suite forces the rule-based path (no GOOGLE_API_KEY, per conftest), so these
run with zero network. The Gemini memory wiring is covered with a fake client.
"""

import pytest

from app.core.budget import _DailyBudget
from app.services.chat import MAX_CONTEXT_MESSAGES, build_context


def _raise_rate_limit(*args, **kwargs):
    """Stand-in for a Gemini 429, so classification buckets it as rate_limited."""
    raise RuntimeError("429 Too Many Requests")


def _fake_genai(monkeypatch, behavior):
    """Patch google.genai.Client with per-model behavior; return the list of models called.

    `behavior` maps a model name to either an Exception (raise it) or nothing
    (a successful canned response). Unlisted models succeed.
    """
    from google import genai

    calls: list[str] = []

    class _Resp:
        text = "answer"
        automatic_function_calling_history = []

    class _Models:
        def generate_content(self, model, contents, config):
            calls.append(model)
            action = behavior.get(model)
            if isinstance(action, Exception):
                raise action
            return _Resp()

    class _Client:
        def __init__(self, **kwargs):
            self.models = _Models()

    monkeypatch.setattr(genai, "Client", _Client)
    return calls


# ── Bounded-context helper ────────────────────────────────────────────────
def test_build_context_trims_to_window():
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(30)]
    ctx = build_context(msgs)
    assert len(ctx) == MAX_CONTEXT_MESSAGES
    assert ctx[-1]["content"] == "m29"  # keeps the most recent


def test_build_context_caps_message_length():
    ctx = build_context([{"role": "user", "content": "x" * 5000}])
    assert len(ctx[0]["content"]) == 2000


# ── Persistence + memory threading ────────────────────────────────────────
def test_send_creates_and_persists_conversation(auth_client):
    r = auth_client.post("/api/conversations/messages", json={"question": "What did I spend?"})
    assert r.status_code == 200
    body = r.json()
    assert body["conversation_id"] > 0
    assert body["title"] == "What did I spend?"
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"]

    detail = auth_client.get(f"/api/conversations/{body['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


def test_follow_up_appends_to_same_thread(auth_client):
    first = auth_client.post("/api/conversations/messages", json={"question": "hi"}).json()
    cid = first["conversation_id"]
    auth_client.post("/api/conversations/messages", json={"conversation_id": cid, "question": "and again"})

    detail = auth_client.get(f"/api/conversations/{cid}").json()
    assert len(detail["messages"]) == 4  # two full exchanges in one thread


def test_prior_turns_are_passed_as_history(auth_client, monkeypatch):
    """The endpoint must thread persisted prior turns into answer_query."""
    seen = {}

    def spy(db, user_id, question, history=None, style="friendly"):
        seen["history"] = history
        seen["style"] = style
        return {"answer": "ok", "provider": "rule-based", "tools_used": []}

    monkeypatch.setattr("app.api.conversations.answer_query", spy)

    first = auth_client.post(
        "/api/conversations/messages", json={"question": "first q", "style": "coach"}
    ).json()
    assert seen["history"] == []  # new thread: no prior context
    assert seen["style"] == "coach"

    auth_client.post(
        "/api/conversations/messages",
        json={"conversation_id": first["conversation_id"], "question": "second q"},
    )
    roles = [h["role"] for h in seen["history"]]
    assert roles == ["user", "assistant"]  # the first exchange became context
    assert seen["history"][0]["content"] == "first q"


def test_list_orders_most_recent_first(auth_client):
    a = auth_client.post("/api/conversations/messages", json={"question": "older"}).json()
    b = auth_client.post("/api/conversations/messages", json={"question": "newer"}).json()
    ids = [c["id"] for c in auth_client.get("/api/conversations").json()]
    assert ids[0] == b["conversation_id"]
    assert a["conversation_id"] in ids


# ── Isolation ─────────────────────────────────────────────────────────────
def test_cross_user_isolation(client, auth_token):
    a_token = auth_token("a@example.com")
    b_token = auth_token("b@example.com")
    client.headers.update({"Authorization": f"Bearer {a_token}"})
    cid = client.post("/api/conversations/messages", json={"question": "mine"}).json()["conversation_id"]

    client.headers.update({"Authorization": f"Bearer {b_token}"})
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.delete(f"/api/conversations/{cid}").status_code == 404
    assert client.post(
        "/api/conversations/messages", json={"conversation_id": cid, "question": "peek"}
    ).status_code == 404
    assert client.get("/api/conversations").json() == []  # B sees none of A's


def test_delete_removes_thread(auth_client):
    cid = auth_client.post("/api/conversations/messages", json={"question": "temp"}).json()["conversation_id"]
    assert auth_client.delete(f"/api/conversations/{cid}").status_code == 204
    assert auth_client.get(f"/api/conversations/{cid}").status_code == 404


# ── Guardrails ────────────────────────────────────────────────────────────
def test_demo_account_cannot_persist(client):
    token = client.post("/api/auth/demo").json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    r = client.post("/api/conversations/messages", json={"question": "save me"})
    assert r.status_code == 403
    # But the stateless demo chat path works.
    assert client.post("/api/query", json={"question": "hello"}).status_code == 200


def test_overlong_question_rejected(auth_client):
    r = auth_client.post("/api/conversations/messages", json={"question": "x" * 501})
    assert r.status_code == 422


def test_query_accepts_history_and_style(auth_client):
    r = auth_client.post(
        "/api/query",
        json={
            "question": "and now?",
            "style": "numbers",
            "history": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hey"}],
        },
    )
    assert r.status_code == 200


# ── Daily budget backstop ─────────────────────────────────────────────────
def test_daily_budget_exhausts_and_resets():
    limit = 2
    b = _DailyBudget(lambda: limit)
    assert b.try_consume() is True
    assert b.try_consume() is True
    assert b.try_consume() is False  # spent
    b._day = None  # simulate day rollover
    assert b.try_consume() is True


def test_budget_spent_raises_without_calling_gemini(db, user, monkeypatch):
    """With a key set but the budget at 0, answer_query raises (never touches Gemini)."""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "test-key")
    monkeypatch.setattr(ai_service.gemini_budget, "_limit_getter", lambda: 0)
    monkeypatch.setattr(ai_service.gemini_budget, "_day", None)

    def boom(*a, **k):  # would be called only if we (wrongly) hit Gemini
        raise AssertionError("Gemini must not be called when budget is spent")

    monkeypatch.setattr("app.services.gemini_provider.gemini_answer", boom)

    with pytest.raises(ai_service.AIUnavailable) as ei:
        ai_service.answer_query(db, user.id, "what did I spend?")
    assert ei.value.reason == "budget"


def test_transient_gemini_failure_raises_not_falls_back(db, user, monkeypatch):
    """Key configured + Gemini errors → retryable AIUnavailable, never a rule-based answer."""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "k")
    monkeypatch.setattr("app.services.gemini_provider.gemini_answer", _raise_rate_limit)

    with pytest.raises(ai_service.AIUnavailable) as ei:
        ai_service.answer_query(db, user.id, "what did I spend?")
    assert ei.value.reason == "rate_limited"


def test_no_key_still_answers_rule_based(db, user, monkeypatch):
    """No API key = offline mode: the deterministic engine IS the answer."""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "")
    out = ai_service.answer_query(db, user.id, "what did I spend?")
    assert out["provider"] == "rule-based"


def test_failed_call_does_not_consume_daily_budget(db, user, monkeypatch):
    """An outage / rate-limit produced no answer, so it must not cost daily budget."""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "k")
    monkeypatch.setattr("app.services.gemini_provider.gemini_answer", _raise_rate_limit)

    before = ai_service.gemini_budget.status()["used"]
    with pytest.raises(ai_service.AIUnavailable):
        ai_service.answer_query(db, user.id, "hi")
    assert ai_service.gemini_budget.status()["used"] == before  # unchanged


def test_successful_call_records_daily_budget(db, user, monkeypatch):
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "k")
    monkeypatch.setattr(
        "app.services.gemini_provider.gemini_answer",
        lambda *a, **k: {"answer": "ok", "provider": "gemini", "tools_used": []},
    )

    before = ai_service.gemini_budget.status()["used"]
    ai_service.answer_query(db, user.id, "hi")
    assert ai_service.gemini_budget.status()["used"] == before + 1


def test_send_returns_503_and_persists_nothing_on_ai_failure(auth_client, monkeypatch):
    """A transient AI failure surfaces as a retryable 503 and creates no thread."""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "k")
    monkeypatch.setattr("app.services.gemini_provider.gemini_answer", _raise_rate_limit)

    r = auth_client.post("/api/conversations/messages", json={"question": "hello"})
    assert r.status_code == 503
    assert r.json()["code"] == "ai_unavailable"
    assert auth_client.get("/api/conversations").json() == []  # nothing half-saved


def test_query_returns_503_on_ai_failure(auth_client, monkeypatch):
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "google_api_key", "k")
    monkeypatch.setattr("app.services.gemini_provider.gemini_answer", _raise_rate_limit)

    r = auth_client.post("/api/query", json={"question": "hi"})
    assert r.status_code == 503
    assert r.json()["code"] == "ai_unavailable"


# ── Gemini memory wiring (fake client, no network) ────────────────────────
def test_gemini_answer_threads_history_and_persona(db, user, monkeypatch):
    from google import genai

    captured = {}

    class _Resp:
        text = "answer"
        automatic_function_calling_history = []

    class _Models:
        def generate_content(self, model, contents, config):
            captured["contents"] = contents
            captured["system"] = config.system_instruction
            return _Resp()

    class _Client:
        def __init__(self, **kwargs):
            self.models = _Models()

    monkeypatch.setattr(genai, "Client", _Client)
    monkeypatch.setattr("app.services.gemini_provider.settings.google_api_key", "k")

    from app.services.gemini_provider import gemini_answer

    history = [
        {"role": "user", "content": "how much on food?"},
        {"role": "assistant", "content": "$120"},
    ]
    out = gemini_answer(db, user.id, "what about March?", history=history, style="coach")

    assert out["answer"] == "answer"
    # history mapped to Gemini roles + the new question appended last
    roles = [c.role for c in captured["contents"]]
    assert roles == ["user", "model", "user"]
    assert captured["contents"][-1].parts[0].text == "what about March?"
    # persona + guardrails present in the system instruction
    assert "You are Jo" in captured["system"]
    assert "SCOPE" in captured["system"]


def test_model_chain_composition(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "google_model", "a")
    monkeypatch.setattr(settings, "google_fallback_models", "b, c , a")  # spaces + dupe
    assert settings.model_chain == ["a", "b", "c"]


def test_model_chain_falls_through_on_quota(db, user, monkeypatch):
    """Primary hits its quota → try the next model; stop at the first success."""
    from app.services import gemini_provider

    monkeypatch.setattr(gemini_provider.settings, "google_api_key", "k")
    monkeypatch.setattr(gemini_provider.settings, "google_model", "m1")
    monkeypatch.setattr(gemini_provider.settings, "google_fallback_models", "m2,m3")

    calls = _fake_genai(monkeypatch, {"m1": RuntimeError("429 RESOURCE_EXHAUSTED")})
    out = gemini_provider.gemini_answer(db, user.id, "hi")

    assert out["answer"] == "answer"
    assert calls == ["m1", "m2"]  # fell through to m2, then stopped


def test_model_chain_falls_through_on_retired_model(db, user, monkeypatch):
    """A retired model 404s (not a quota error) — the chain must route around it."""
    from app.services import gemini_provider

    monkeypatch.setattr(gemini_provider.settings, "google_api_key", "k")
    monkeypatch.setattr(gemini_provider.settings, "google_model", "old")
    monkeypatch.setattr(gemini_provider.settings, "google_fallback_models", "new")

    err = RuntimeError("404 NOT_FOUND: model is no longer available to new users")
    calls = _fake_genai(monkeypatch, {"old": err})
    out = gemini_provider.gemini_answer(db, user.id, "hi")

    assert out["answer"] == "answer"
    assert calls == ["old", "new"]


def test_model_chain_falls_through_on_503(db, user, monkeypatch):
    """An overloaded (503) model should route to the next, not just error out."""
    from app.services import gemini_provider

    monkeypatch.setattr(gemini_provider.settings, "google_api_key", "k")
    monkeypatch.setattr(gemini_provider.settings, "google_model", "m1")
    monkeypatch.setattr(gemini_provider.settings, "google_fallback_models", "m2")

    err = RuntimeError("503 UNAVAILABLE. The model is overloaded. Please try again later.")
    calls = _fake_genai(monkeypatch, {"m1": err})
    out = gemini_provider.gemini_answer(db, user.id, "hi")

    assert out["answer"] == "answer"
    assert calls == ["m1", "m2"]


def test_model_chain_non_quota_error_raises_immediately(db, user, monkeypatch):
    """A non-quota failure must NOT burn the other models — it propagates at once."""
    from app.services import gemini_provider

    monkeypatch.setattr(gemini_provider.settings, "google_api_key", "k")
    monkeypatch.setattr(gemini_provider.settings, "google_model", "m1")
    monkeypatch.setattr(gemini_provider.settings, "google_fallback_models", "m2")

    calls = _fake_genai(monkeypatch, {"m1": ValueError("malformed request")})
    with pytest.raises(ValueError):
        gemini_provider.gemini_answer(db, user.id, "hi")
    assert calls == ["m1"]  # m2 never tried


def test_all_models_exhausted_surfaces_retryable(db, user, monkeypatch):
    """Every model quota-limited → a retryable AIUnavailable, never a rule-based answer."""
    from app.services import ai_service, gemini_provider

    monkeypatch.setattr(ai_service.settings, "google_api_key", "k")
    monkeypatch.setattr(gemini_provider.settings, "google_model", "m1")
    monkeypatch.setattr(gemini_provider.settings, "google_fallback_models", "m2")

    err = RuntimeError("429 RESOURCE_EXHAUSTED")
    calls = _fake_genai(monkeypatch, {"m1": err, "m2": err})
    with pytest.raises(ai_service.AIUnavailable) as ei:
        ai_service.answer_query(db, user.id, "hi")
    assert ei.value.reason == "rate_limited"
    assert calls == ["m1", "m2"]


def test_normalize_style_clamps_unknown():
    from app.services.gemini_provider import normalize_style

    assert normalize_style("coach") == "coach"
    assert normalize_style("nonsense") == "friendly"
    assert normalize_style(None) == "friendly"


@pytest.mark.parametrize("style", ["friendly", "numbers", "coach"])
def test_all_styles_accepted(auth_client, style):
    r = auth_client.post("/api/conversations/messages", json={"question": "hi", "style": style})
    assert r.status_code == 200
