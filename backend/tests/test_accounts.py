"""Phase 22: account balances (Plaid + demo sample accounts) and Jo's balances tool."""

from sqlalchemy import select

from app.models.models import Account
from app.services import tools
from app.services.ai_service import fallback_answer
from tests.test_plaid import _configure, _stub_exchange

CHECKING = {"external_id": "acc-1", "name": "Plaid Checking", "mask": "0000",
            "type": "depository", "subtype": "checking",
            "current_balance": 1000.0, "available_balance": 900.0, "currency": "USD"}
CARD = {"external_id": "acc-2", "name": "Plaid Credit Card", "mask": "3333",
        "type": "credit", "subtype": "credit card",
        "current_balance": 250.0, "available_balance": 1750.0, "currency": "USD"}


def test_no_accounts_is_empty_not_error(auth_client):
    r = auth_client.get("/api/account/balances")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0 and body["net_worth"] == 0 and body["accounts"] == []


def test_balances_require_auth(client):
    assert client.get("/api/account/balances").status_code == 401


def test_exchange_stores_accounts_and_nets_credit_as_debt(auth_client, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch, accounts=[CHECKING, CARD])
    auth_client.post("/api/plaid/exchange", json={"public_token": "p"})

    body = auth_client.get("/api/account/balances").json()
    assert body["count"] == 2
    assert body["assets"] == 1000.0
    assert body["liabilities"] == 250.0     # card balance is money owed
    assert body["net_worth"] == 750.0
    assert body["sample"] is False
    # Money held listed before money owed.
    assert [a["name"] for a in body["accounts"]] == ["Plaid Checking", "Plaid Credit Card"]
    assert body["accounts"][1]["is_liability"] is True
    assert body["accounts"][0]["institution"] == "Test Bank"


def test_bank_connected_flag_even_before_balances_load(auth_client, monkeypatch):
    """A pre-Phase-22 connection has an item but no account rows: UI must offer refresh."""
    assert auth_client.get("/api/account/balances").json()["bank_connected"] is False
    _configure(monkeypatch)
    _stub_exchange(monkeypatch)  # accounts=() → no rows stored
    auth_client.post("/api/plaid/exchange", json={"public_token": "p"})
    body = auth_client.get("/api/account/balances").json()
    assert body["count"] == 0 and body["bank_connected"] is True


def test_sync_refreshes_balances_without_duplicating(auth_client, db, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch, accounts=[CHECKING])
    auth_client.post("/api/plaid/exchange", json={"public_token": "p"})

    from app.services import plaid_client
    monkeypatch.setattr(plaid_client, "sync_transactions", lambda at, cur: ([], "c1"))
    monkeypatch.setattr(plaid_client, "get_accounts",
                        lambda at: [{**CHECKING, "current_balance": 1500.0}])
    auth_client.post("/api/plaid/sync")

    rows = db.scalars(select(Account)).all()
    assert len(rows) == 1
    assert rows[0].current_balance == 1500.0


def test_balance_failure_does_not_break_sync(auth_client, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch)
    auth_client.post("/api/plaid/exchange", json={"public_token": "p"})

    from app.services import plaid_client

    def boom(at):
        raise RuntimeError("plaid down")

    monkeypatch.setattr(plaid_client, "sync_transactions", lambda at, cur: ([], "c1"))
    monkeypatch.setattr(plaid_client, "get_accounts", boom)
    assert auth_client.post("/api/plaid/sync").status_code == 200


def test_accounts_are_per_user(client, auth_token, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch, accounts=[CHECKING])
    a = auth_token("a@example.com")
    b = auth_token("b@example.com")

    client.headers.update({"Authorization": f"Bearer {a}"})
    client.post("/api/plaid/exchange", json={"public_token": "p"})
    client.headers.update({"Authorization": f"Bearer {b}"})
    assert client.get("/api/account/balances").json()["count"] == 0


def test_demo_gets_labeled_sample_accounts_once(client):
    token = client.post("/api/auth/demo").json()["access_token"]
    client.post("/api/auth/demo")  # second entry must not re-seed
    client.headers.update({"Authorization": f"Bearer {token}"})

    body = client.get("/api/account/balances").json()
    assert body["count"] == 3
    assert body["sample"] is True
    assert body["net_worth"] == round(3842.17 + 11250.00 - 1286.43, 2)


def test_clear_data_removes_accounts(auth_client, db, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch, accounts=[CHECKING])
    auth_client.post("/api/plaid/exchange", json={"public_token": "p"})
    auth_client.post("/api/account/clear-data")
    assert db.scalar(select(Account)) is None


def test_balances_tool_flags_sample_for_jo(db, user):
    from app.services.accounts import seed_sample_accounts
    seed_sample_accounts(db, user.id)
    db.commit()
    out = tools.account_balances(db, user.id)
    assert out["sample"] is True and "sample" in out["note"]


def test_fallback_answers_balance_questions(db, user):
    answer, used = fallback_answer(db, user.id, "What's my balance?")
    assert used == ["account_balances"] and "connect a bank" in answer

    from app.services.accounts import seed_sample_accounts
    seed_sample_accounts(db, user.id)
    db.commit()
    answer, _ = fallback_answer(db, user.id, "how much money do I have?")
    assert "net worth" in answer and "sample" in answer
