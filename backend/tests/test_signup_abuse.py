"""Phase 17: signup abuse prevention — disposable-email blocklist + Turnstile CAPTCHA.

CAPTCHA is off by default (no TURNSTILE_SECRET in the test env), so existing auth
tests keep registering without a token; the CAPTCHA cases enable it explicitly.
"""

from app.core import captcha
from app.core.email_rules import is_disposable


class _FakeResp:
    def __init__(self, success: bool):
        self._success = success

    def json(self):
        return {"success": self._success}


# ── Disposable-email blocklist (always on, offline) ───────────────────────
def test_is_disposable_matches_known_domains():
    assert is_disposable("bot@mailinator.com") is True
    assert is_disposable("x@guerrillamail.com") is True
    assert is_disposable("real.person@gmail.com") is False
    assert is_disposable("me@example.com") is False


def test_is_disposable_is_case_insensitive():
    assert is_disposable("Bot@MailInator.com") is True


def test_register_rejects_disposable_email(client):
    r = client.post("/api/auth/register", json={"email": "bot@mailinator.com", "password": "pw123456"})
    assert r.status_code == 400
    assert "disposable" in r.json()["detail"].lower()


def test_register_allows_normal_email(client):
    r = client.post("/api/auth/register", json={"email": "real@example.com", "password": "pw123456"})
    assert r.status_code == 201


# ── Turnstile verifier (unit) ─────────────────────────────────────────────
def test_verify_disabled_returns_true(monkeypatch):
    monkeypatch.setattr(captcha.settings, "turnstile_secret", "")
    assert captcha.verify_turnstile(None) is True  # no key → skipped


def test_verify_rejects_missing_token_when_enabled(monkeypatch):
    monkeypatch.setattr(captcha.settings, "turnstile_secret", "secret")
    assert captcha.verify_turnstile(None) is False


def test_verify_uses_cloudflare_verdict(monkeypatch):
    monkeypatch.setattr(captcha.settings, "turnstile_secret", "secret")
    monkeypatch.setattr(captcha.httpx, "post", lambda *a, **k: _FakeResp(True))
    assert captcha.verify_turnstile("good-token") is True
    monkeypatch.setattr(captcha.httpx, "post", lambda *a, **k: _FakeResp(False))
    assert captcha.verify_turnstile("bad-token") is False


def test_verify_fails_closed_on_network_error(monkeypatch):
    monkeypatch.setattr(captcha.settings, "turnstile_secret", "secret")

    def boom(*a, **k):
        raise RuntimeError("cloudflare unreachable")

    monkeypatch.setattr(captcha.httpx, "post", boom)
    assert captcha.verify_turnstile("token") is False  # outage can't bypass the gate


# ── CAPTCHA gate on the register endpoint ─────────────────────────────────
def test_register_blocks_invalid_captcha(client, monkeypatch):
    monkeypatch.setattr(captcha.settings, "turnstile_secret", "secret")
    monkeypatch.setattr(captcha.httpx, "post", lambda *a, **k: _FakeResp(False))
    r = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "pw123456", "turnstile_token": "bad"},
    )
    assert r.status_code == 400
    assert "captcha" in r.json()["detail"].lower()


def test_register_passes_valid_captcha(client, monkeypatch):
    monkeypatch.setattr(captcha.settings, "turnstile_secret", "secret")
    monkeypatch.setattr(captcha.httpx, "post", lambda *a, **k: _FakeResp(True))
    r = client.post(
        "/api/auth/register",
        json={"email": "new2@example.com", "password": "pw123456", "turnstile_token": "good"},
    )
    assert r.status_code == 201
