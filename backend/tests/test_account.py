"""Phase 18 add-on: clearing your own account data."""

from sqlalchemy import func, select

from app.models.models import Transaction, Upload


def test_clear_data_removes_everything_for_the_user(auth_client, db):
    auth_client.post("/api/load-sample")
    assert db.scalar(select(func.count()).select_from(Transaction)) > 0

    r = auth_client.post("/api/account/clear-data")
    assert r.status_code == 200
    assert r.json()["transactions_deleted"] > 0

    assert db.scalar(select(func.count()).select_from(Transaction)) == 0
    assert db.scalar(select(func.count()).select_from(Upload)) == 0
    # Account still works afterwards.
    assert auth_client.get("/api/transactions").json()["total"] == 0


def test_clear_data_is_scoped_to_the_current_user(client, auth_token):
    a = auth_token("a@example.com")
    b = auth_token("b@example.com")

    client.headers.update({"Authorization": f"Bearer {a}"})
    client.post("/api/load-sample")
    client.headers.update({"Authorization": f"Bearer {b}"})
    client.post("/api/load-sample")

    # B clears — A must be untouched.
    client.post("/api/account/clear-data")
    assert client.get("/api/transactions").json()["total"] == 0

    client.headers.update({"Authorization": f"Bearer {a}"})
    assert client.get("/api/transactions").json()["total"] > 0


def test_demo_data_cannot_be_cleared(client):
    """The demo is shared: one visitor must not be able to empty it for everyone."""
    token = client.post("/api/auth/demo").json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    before = client.get("/api/transactions", headers=h).json()["total"]
    assert client.post("/api/account/clear-data", headers=h).status_code == 403
    assert client.get("/api/transactions", headers=h).json()["total"] == before > 0


def test_clear_data_requires_auth(client):
    assert client.post("/api/account/clear-data").status_code == 401
