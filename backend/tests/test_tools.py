"""Query-tool tests: computed totals and the subscription/bill split."""

import datetime

from app.models.models import Subscription, Transaction, Upload
from app.services import tools


def _upload(db):
    upload = Upload(filename="t", row_count=0, status="complete")
    db.add(upload)
    db.flush()
    return upload


def test_totals_and_category_spend(db):
    upload = _upload(db)
    db.add_all([
        Transaction(upload_id=upload.id, date=datetime.date(2024, 1, 1), description="a",
                    merchant_normalized="A", amount=100.0, transaction_type="debit",
                    category="groceries", category_confidence=0.9),
        Transaction(upload_id=upload.id, date=datetime.date(2024, 1, 2), description="b",
                    merchant_normalized="B", amount=-2000.0, transaction_type="credit",
                    category="income", category_confidence=0.9),
    ])
    db.commit()

    assert tools.get_total(db, "spending")["total"] == 100.0
    assert tools.get_total(db, "income")["total"] == 2000.0
    assert tools.get_spending_by_category(db, "groceries")["total"] == 100.0


def test_subscription_bill_split(db):
    upload = _upload(db)
    db.add(Subscription(upload_id=upload.id, merchant_normalized="NETFLIX", amount=16.0,
                        frequency="monthly", last_charged=datetime.date(2024, 1, 1),
                        occurrence_count=3, total_spent=48.0, category="subscriptions",
                        kind="subscription"))
    db.add(Subscription(upload_id=upload.id, merchant_normalized="RENT", amount=1800.0,
                        frequency="monthly", last_charged=datetime.date(2024, 1, 1),
                        occurrence_count=3, total_spent=5400.0, category="rent", kind="bill"))
    db.commit()

    assert tools.list_subscriptions(db)["count"] == 1
    assert tools.list_subscriptions(db)["monthly_cost"] == 16.0
    assert tools.list_recurring_bills(db)["count"] == 1
    assert tools.list_recurring_bills(db)["monthly_cost"] == 1800.0
