"""API integration tests: auth, the upload flow, and per-user isolation."""


def test_health_is_public(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_protected_endpoint_requires_auth(client):
    """Without a token, data endpoints reject with 401."""
    assert client.get("/api/transactions").status_code == 401
    assert client.get("/api/analytics/summary").status_code == 401


def test_register_and_login(client):
    r = client.post("/api/auth/register", json={"email": "new@example.com", "password": "pw123456"})
    assert r.status_code == 201
    assert r.json()["email"] == "new@example.com"

    r = client.post("/api/auth/login", data={"username": "new@example.com", "password": "pw123456"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "x@example.com", "password": "correct1"})
    r = client.post("/api/auth/login", data={"username": "x@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_upload_read_and_analyze(auth_client, sample_csv):
    with open(sample_csv, "rb") as fh:
        resp = auth_client.post("/api/upload", files={"file": ("chase_sample.csv", fh, "text/csv")})
    assert resp.status_code == 200
    result = resp.json()
    assert result["row_count"] > 0
    assert result["error_count"] == 0

    tx = auth_client.get("/api/transactions", params={"page_size": 5}).json()
    assert tx["total"] == result["row_count"]

    assert len(auth_client.get("/api/subscriptions").json()) >= 1
    assert len(auth_client.get("/api/anomalies").json()) >= 1

    summary = auth_client.get("/api/analytics/summary").json()
    assert summary["transaction_count"] == result["row_count"]

    q = auth_client.post("/api/query", json={"question": "how many subscriptions do I have?"}).json()
    assert q["provider"] == "rule-based"
    assert "subscription" in q["answer"].lower()


def test_load_sample_endpoint(auth_client):
    assert auth_client.post("/api/load-sample").json()["row_count"] > 0


def test_upload_rejects_non_csv(auth_client):
    resp = auth_client.post("/api/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_user_isolation(client, auth_token, sample_csv):
    """User B must never see User A's financial data."""
    ha = {"Authorization": f"Bearer {auth_token('a@example.com')}"}
    hb = {"Authorization": f"Bearer {auth_token('b@example.com')}"}

    # A uploads data.
    with open(sample_csv, "rb") as fh:
        client.post("/api/upload", files={"file": ("c.csv", fh, "text/csv")}, headers=ha)

    # A sees their data.
    assert client.get("/api/transactions", headers=ha).json()["total"] > 0

    # B sees nothing across every surface.
    assert client.get("/api/transactions", headers=hb).json()["total"] == 0
    assert client.get("/api/subscriptions", headers=hb).json() == []
    assert client.get("/api/anomalies", headers=hb).json() == []
    assert client.get("/api/analytics/summary", headers=hb).json()["transaction_count"] == 0
