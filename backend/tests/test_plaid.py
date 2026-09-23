"""Phase 18: Plaid sandbox connect flow — all mocked, no network.

Plaid is disabled by default (no keys in the test env), so the endpoints 503;
the connected-flow tests enable it and stub the Plaid client. Access tokens are
stored encrypted; the sync path flows through the shared persist pipeline.
"""

import datetime

import pytest
from sqlalchemy import select

from app.core import crypto
from app.models.models import PlaidItem, Transaction, Upload


def _configure(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "plaid_client_id", "test-id")
    monkeypatch.setattr(settings, "plaid_secret", "test-secret")


def _stub_exchange(monkeypatch, item_id="item-123", token="access-secret-xyz", inst="Test Bank",
                   accounts=()):
    from app.services import plaid_client
    monkeypatch.setattr(plaid_client, "exchange_public_token", lambda pt: (item_id, token))
    monkeypatch.setattr(plaid_client, "get_institution_name", lambda at: inst)
    monkeypatch.setattr(plaid_client, "get_accounts", lambda at: list(accounts))


# ── Feature flag / status ─────────────────────────────────────────────────
def test_status_reflects_configuration(auth_client, monkeypatch):
    assert auth_client.get("/api/plaid/status").json()["configured"] is False
    _configure(monkeypatch)
    assert auth_client.get("/api/plaid/status").json()["configured"] is True


def test_endpoints_503_when_unconfigured(auth_client):
    assert auth_client.post("/api/plaid/link-token").status_code == 503
    assert auth_client.post("/api/plaid/exchange", json={"public_token": "x"}).status_code == 503
    assert auth_client.post("/api/plaid/sync").status_code == 503


# ── Crypto ────────────────────────────────────────────────────────────────
def test_token_encryption_roundtrip():
    ct = crypto.encrypt("super-secret-access-token")
    assert ct != "super-secret-access-token"  # not stored in the clear
    assert crypto.decrypt(ct) == "super-secret-access-token"


# ── Link + exchange ───────────────────────────────────────────────────────
def test_link_token_returned(auth_client, monkeypatch):
    _configure(monkeypatch)
    from app.services import plaid_client
    monkeypatch.setattr(plaid_client, "create_link_token", lambda uid: "link-tok-abc")
    r = auth_client.post("/api/plaid/link-token")
    assert r.status_code == 200
    assert r.json()["link_token"] == "link-tok-abc"


def test_exchange_stores_encrypted_item(auth_client, db, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch)
    r = auth_client.post("/api/plaid/exchange", json={"public_token": "public-xyz"})
    assert r.status_code == 200
    assert r.json() == {"item_id": "item-123", "institution_name": "Test Bank"}

    item = db.scalar(select(PlaidItem))
    assert item.item_id == "item-123"
    assert item.access_token != "access-secret-xyz"          # stored encrypted
    assert crypto.decrypt(item.access_token) == "access-secret-xyz"


def test_exchange_replaces_existing_item(auth_client, db, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch, item_id="item-A", token="tok-A")
    auth_client.post("/api/plaid/exchange", json={"public_token": "p1"})
    _stub_exchange(monkeypatch, item_id="item-B", token="tok-B")
    auth_client.post("/api/plaid/exchange", json={"public_token": "p2"})

    items = db.scalars(select(PlaidItem)).all()
    assert len(items) == 1  # single item per user
    assert items[0].item_id == "item-B"


# ── Sync ──────────────────────────────────────────────────────────────────
def test_sync_ingests_transactions_through_pipeline(auth_client, db, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch)
    auth_client.post("/api/plaid/exchange", json={"public_token": "p"})

    rows = [
        {"date": datetime.date(2024, 3, 1), "description": "STARBUCKS",
         "merchant_normalized": "Starbucks", "amount": 5.50, "transaction_type": "debit"},
        {"date": datetime.date(2024, 3, 2), "description": "PAYROLL",
         "merchant_normalized": "Employer", "amount": -2000.0, "transaction_type": "credit"},
    ]
    from app.services import plaid_client
    monkeypatch.setattr(plaid_client, "sync_transactions", lambda at, cur: (rows, "cursor-1"))

    r = auth_client.post("/api/plaid/sync")
    assert r.status_code == 200
    assert r.json()["added"] == 2

    txns = db.scalars(select(Transaction)).all()
    assert len(txns) == 2
    upload = db.scalar(select(Upload))
    assert upload.source == "plaid"
    item = db.scalar(select(PlaidItem))
    assert item.cursor == "cursor-1"  # saved for the next incremental sync


def test_sync_without_connected_bank_404s(auth_client, monkeypatch):
    _configure(monkeypatch)
    assert auth_client.post("/api/plaid/sync").status_code == 404


# ── Isolation ─────────────────────────────────────────────────────────────
def test_plaid_item_is_per_user(client, auth_token, monkeypatch):
    _configure(monkeypatch)
    _stub_exchange(monkeypatch, item_id="item-A", token="tok-A")
    a = auth_token("a@example.com")
    b = auth_token("b@example.com")

    client.headers.update({"Authorization": f"Bearer {a}"})
    client.post("/api/plaid/exchange", json={"public_token": "pt"})

    client.headers.update({"Authorization": f"Bearer {b}"})
    assert client.post("/api/plaid/sync").status_code == 404  # B has no item of their own


def test_csv_upload_still_marked_source_csv(auth_client, db, sample_csv):
    with open(sample_csv, "rb") as f:
        auth_client.post("/api/upload", files={"file": ("chase_sample.csv", f, "text/csv")})
    upload = db.scalar(select(Upload))
    assert upload.source == "csv"


@pytest.mark.parametrize("amount,expected", [(5.5, "debit"), (-10.0, "credit")])
def test_plaid_row_mapping_sign_convention(amount, expected):
    """A synced row's type must follow our sign convention (positive=expense=debit)."""
    from app.services.plaid_client import _to_row

    class _Txn:
        def __init__(self, amt):
            self.amount = amt
            self.name = "X"
            self.merchant_name = "X"
            self.date = datetime.date(2024, 1, 1)

    assert _to_row(_Txn(amount))["transaction_type"] == expected
