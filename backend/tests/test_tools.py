"""Query-tool tests: computed totals, the subscription/bill split, all user-scoped."""

import datetime

from app.models.models import Subscription, Transaction, Upload
from app.services import tools


def _upload(db, user_id):
    upload = Upload(user_id=user_id, filename="t", row_count=0, status="complete")
    db.add(upload)
    db.flush()
    return upload


def test_totals_and_category_spend(db, user):
    upload = _upload(db, user.id)
    db.add_all([
        Transaction(upload_id=upload.id, user_id=user.id, date=datetime.date(2024, 1, 1),
                    description="a", merchant_normalized="A", amount=100.0,
                    transaction_type="debit", category="groceries", category_confidence=0.9),
        Transaction(upload_id=upload.id, user_id=user.id, date=datetime.date(2024, 1, 2),
                    description="b", merchant_normalized="B", amount=-2000.0,
                    transaction_type="credit", category="income", category_confidence=0.9),
    ])
    db.commit()

    assert tools.get_total(db, user.id, "spending")["total"] == 100.0
    assert tools.get_total(db, user.id, "income")["total"] == 2000.0
    assert tools.get_spending_by_category(db, user.id, "groceries")["total"] == 100.0


def test_subscription_bill_split(db, user):
    upload = _upload(db, user.id)
    db.add(Subscription(upload_id=upload.id, user_id=user.id, merchant_normalized="NETFLIX",
                        amount=16.0, frequency="monthly", last_charged=datetime.date(2024, 1, 1),
                        occurrence_count=3, total_spent=48.0, category="subscriptions",
                        kind="subscription"))
    db.add(Subscription(upload_id=upload.id, user_id=user.id, merchant_normalized="RENT",
                        amount=1800.0, frequency="monthly", last_charged=datetime.date(2024, 1, 1),
                        occurrence_count=3, total_spent=5400.0, category="rent", kind="bill"))
    db.commit()

    assert tools.list_subscriptions(db, user.id)["count"] == 1
    assert tools.list_subscriptions(db, user.id)["monthly_cost"] == 16.0
    assert tools.list_recurring_bills(db, user.id)["count"] == 1
    assert tools.list_recurring_bills(db, user.id)["monthly_cost"] == 1800.0
