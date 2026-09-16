"""Phase 16: token revocation, rate limiting, upload validation, log redaction."""

import json
import logging

from app.core.logging import _SECRET_KEYS, JsonFormatter, _scrub

# --- Token revocation (token_version) ---------------------------------------

def test_logout_all_revokes_existing_token(client, auth_token):
    token = auth_token("rev@example.com")
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/transactions", headers=h).status_code == 200
    assert client.post("/api/auth/logout-all", headers=h).status_code == 200
    # The same token is now stale (version bumped) -> rejected.
    assert client.get("/api/transactions", headers=h).status_code == 401


def test_change_password_wrong_current_rejected(client, auth_token):
    h = {"Authorization": f"Bearer {auth_token('cp1@example.com')}"}
    r = client.post(
        "/api/auth/change-password",
        headers=h,
        json={"current_password": "wrongpass", "new_password": "newpass12"},
    )
    assert r.status_code == 401


def test_change_password_revokes_old_and_new_works(client, auth_token):
    h = {"Authorization": f"Bearer {auth_token('cp2@example.com')}"}  # pw123456
    r = client.post(
        "/api/auth/change-password",
        headers=h,
        json={"current_password": "pw123456", "new_password": "newpass12"},
    )
    assert r.status_code == 200
    assert client.get("/api/transactions", headers=h).status_code == 401  # old token dead

    ok = client.post("/api/auth/login", data={"username": "cp2@example.com", "password": "newpass12"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = client.post("/api/auth/login", data={"username": "cp2@example.com", "password": "pw123456"})
    assert bad.status_code == 401


# --- Rate limiting -----------------------------------------------------------

def test_login_is_rate_limited(client):
    from app.core.ratelimit import limiter
    limiter.enabled = True
    try:
        codes = [
            client.post("/api/auth/login", data={"username": "nobody@example.com", "password": "x"}).status_code
            for _ in range(7)
        ]
        assert 429 in codes  # 5/minute cap tripped
    finally:
        limiter.enabled = False


# --- Upload validation -------------------------------------------------------

def test_upload_rejects_oversized(auth_client, monkeypatch):
    import app.api.upload as up
    monkeypatch.setattr(up, "MAX_UPLOAD_BYTES", 10)
    r = auth_client.post("/api/upload", files={"file": ("big.csv", b"x" * 500, "text/csv")})
    assert r.status_code == 413


def test_upload_rejects_empty(auth_client):
    r = auth_client.post("/api/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_upload_rejects_too_many_rows(client, auth_token, sample_csv, monkeypatch):
    import app.api.upload as up
    monkeypatch.setattr(up, "MAX_ROWS", 2)
    h = {"Authorization": f"Bearer {auth_token('rows@example.com')}"}
    with open(sample_csv, "rb") as fh:
        r = client.post("/api/upload", files={"file": ("s.csv", fh, "text/csv")}, headers=h)
    assert r.status_code == 413


# --- Log redaction -----------------------------------------------------------

def test_scrub_redacts_bearer_tokens():
    assert _scrub("Authorization: Bearer abc.def-ghi") == "Authorization: Bearer [REDACTED]"
    assert _scrub("no secrets here") == "no secrets here"
    assert "password" in _SECRET_KEYS and "token" in _SECRET_KEYS


def test_formatter_redacts_secret_extras():
    rec = logging.LogRecord("t", logging.INFO, "f", 1, "msg", None, None)
    rec.password = "hunter2"
    rec.note = "sent Bearer xyz.abc123"
    out = json.loads(JsonFormatter().format(rec))
    assert out["password"] == "[REDACTED]"
    assert out["note"] == "sent Bearer [REDACTED]"
