"""Phase 22: password strength rules on register and change-password."""

import pytest

from app.core.password_policy import password_error, password_problems


@pytest.mark.parametrize("pw,missing", [
    ("Sh0rt!", "at least 8 characters"),
    ("lowercase1!", "an uppercase letter"),
    ("UPPERCASE1!", "a lowercase letter"),
    ("NoNumbers!", "a number"),
    ("NoSymbol123", "a symbol"),
])
def test_each_rule_is_enforced(pw, missing):
    assert missing in password_problems(pw)


def test_strong_password_passes():
    assert password_problems("Str0ng!Pass") == []
    assert password_error("Str0ng!Pass") is None


def test_overlong_password_rejected():
    # bcrypt ignores bytes past 72, so we cap well below that.
    assert password_problems("Aa1!" * 20) == ["at most 64 characters"]


def test_register_rejects_weak_password_with_clear_message(client):
    r = client.post("/api/auth/register", json={"email": "weak@example.com", "password": "password"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail.startswith("Password needs")
    assert "an uppercase letter" in detail and "a number" in detail and "a symbol" in detail


def test_register_accepts_strong_password(client):
    r = client.post("/api/auth/register", json={"email": "ok@example.com", "password": "Str0ng!Pass"})
    assert r.status_code == 201


def test_change_password_enforces_rules(client, auth_token):
    token = auth_token("cp@example.com")
    r = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "Pw12345!", "new_password": "weakpass"},
    )
    assert r.status_code == 400
    assert r.json()["detail"].startswith("Password needs")
