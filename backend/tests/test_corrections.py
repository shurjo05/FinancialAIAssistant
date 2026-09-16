"""Phase 14: category corrections (training signal + audit) and low-confidence surfacing."""

import datetime

from sqlalchemy import select

from app.models.models import Transaction, Upload, User


def _first_txn(client):
    return client.get("/api/transactions", params={"page_size": 1}).json()["items"][0]


def test_correct_category_records_correction(auth_client):
    auth_client.post("/api/load-sample")
    txn = _first_txn(auth_client)
    tid, original = txn["id"], txn["category"]
    new = "groceries" if original != "groceries" else "restaurants"

    r = auth_client.patch(f"/api/transactions/{tid}/category", json={"category": new})
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == new
    assert body["category_confidence"] == 1.0  # human ground truth

    corr = auth_client.get("/api/corrections").json()
    assert len(corr) == 1
    assert corr[0]["transaction_id"] == tid
    assert corr[0]["original_category"] == original
    assert corr[0]["corrected_category"] == new
    # model_version is "1" when the model is loaded locally, None in rules-only CI.
    assert corr[0]["model_version"] in ("1", None)


def test_correct_category_rejects_unknown(auth_client):
    auth_client.post("/api/load-sample")
    tid = _first_txn(auth_client)["id"]
    r = auth_client.patch(f"/api/transactions/{tid}/category", json={"category": "not-a-category"})
    assert r.status_code == 422


def test_correct_category_is_user_isolated(client, auth_token, sample_csv):
    ha = {"Authorization": f"Bearer {auth_token('ca@example.com')}"}
    hb = {"Authorization": f"Bearer {auth_token('cb@example.com')}"}
    with open(sample_csv, "rb") as fh:
        client.post("/api/upload", files={"file": ("c.csv", fh, "text/csv")}, headers=ha)
    tid = client.get("/api/transactions", params={"page_size": 1}, headers=ha).json()["items"][0]["id"]

    # B cannot correct A's transaction.
    r = client.patch(f"/api/transactions/{tid}/category", json={"category": "groceries"}, headers=hb)
    assert r.status_code == 404
    # And B sees none of A's corrections.
    assert client.get("/api/corrections", headers=hb).json() == []


def test_low_confidence_filter(client, auth_token, db):
    token = auth_token("lc@example.com")
    hdr = {"Authorization": f"Bearer {token}"}
    u = db.scalar(select(User).where(User.email == "lc@example.com"))
    up = Upload(user_id=u.id, filename="x.csv", row_count=2, status="complete")
    db.add(up)
    db.flush()
    for merch, conf, cat in [("mystery", 0.1, "shopping"), ("clear", 0.99, "groceries")]:
        db.add(Transaction(
            upload_id=up.id, user_id=u.id, date=datetime.date(2024, 1, 1),
            description=merch.upper(), merchant_normalized=merch, amount=10.0,
            transaction_type="debit", category=cat, category_confidence=conf,
            is_recurring=False, is_anomaly=False,
        ))
    db.commit()

    items = client.get("/api/transactions", params={"low_confidence": "true"}, headers=hdr).json()["items"]
    confidences = [r["category_confidence"] for r in items]
    assert confidences and all(c < 0.5 for c in confidences)  # only unsure rows
    assert any(r["merchant_normalized"] == "mystery" for r in items)
    assert not any(r["merchant_normalized"] == "clear" for r in items)
