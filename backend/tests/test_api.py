"""API integration tests: the upload -> read -> analyze -> query flow via TestClient."""


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_upload_read_and_analyze(client, sample_csv):
    with open(sample_csv, "rb") as fh:
        resp = client.post("/api/upload", files={"file": ("chase_sample.csv", fh, "text/csv")})
    assert resp.status_code == 200
    result = resp.json()
    assert result["row_count"] > 0
    assert result["error_count"] == 0

    # transactions persisted
    tx = client.get("/api/transactions", params={"page_size": 5}).json()
    assert tx["total"] == result["row_count"]
    assert len(tx["items"]) == 5

    # detectors ran (background task, executed synchronously by TestClient)
    assert len(client.get("/api/subscriptions").json()) >= 1
    assert len(client.get("/api/anomalies").json()) >= 1

    # analytics reflect the upload
    summary = client.get("/api/analytics/summary").json()
    assert summary["transaction_count"] == result["row_count"]
    assert summary["total_income"] > 0

    # NL query uses the deterministic fallback (no API key in tests)
    q = client.post("/api/query", json={"question": "how many subscriptions do I have?"}).json()
    assert q["provider"] == "rule-based"
    assert "subscription" in q["answer"].lower()


def test_load_sample_endpoint(client):
    resp = client.post("/api/load-sample")
    assert resp.status_code == 200
    assert resp.json()["row_count"] > 0


def test_upload_rejects_non_csv(client):
    resp = client.post("/api/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_category_filter(client, sample_csv):
    with open(sample_csv, "rb") as fh:
        client.post("/api/upload", files={"file": ("chase_sample.csv", fh, "text/csv")})
    filtered = client.get("/api/transactions", params={"category": "restaurants"}).json()
    assert all(t["category"] == "restaurants" for t in filtered["items"])
