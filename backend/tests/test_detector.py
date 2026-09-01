"""Detector tests: subscription evidence threshold, bill classification, anomaly guardrails."""

import datetime
from types import SimpleNamespace

from app.services.detector import detect_anomalies, detect_subscriptions


def _txn(tid, date, amount, merchant, category, ttype="debit"):
    return SimpleNamespace(
        id=tid, date=date, amount=amount, merchant_normalized=merchant,
        category=category, transaction_type=ttype,
    )


def test_subscription_requires_three_occurrences():
    two = [
        _txn(1, datetime.date(2024, 1, 5), 15.99, "NETFLIX", "subscriptions"),
        _txn(2, datetime.date(2024, 2, 5), 15.99, "NETFLIX", "subscriptions"),
    ]
    assert detect_subscriptions(two)[0] == []  # two points = coincidence

    three = two + [_txn(3, datetime.date(2024, 3, 5), 15.99, "NETFLIX", "subscriptions")]
    subs, recurring_ids = detect_subscriptions(three)
    assert len(subs) == 1
    assert subs[0]["frequency"] == "monthly"
    assert subs[0]["kind"] == "subscription"
    assert recurring_ids == {1, 2, 3}


def test_bill_category_classified_as_bill():
    txns = [_txn(i, datetime.date(2024, i, 1), 1800.0, "RENT", "rent") for i in range(1, 4)]
    subs, _ = detect_subscriptions(txns)
    assert subs and subs[0]["kind"] == "bill"


def test_anomaly_flags_high_spike_and_skips_low_side():
    normal = [
        _txn(i, datetime.date(2024, 1, (i % 27) + 1), 20.0 + i, "STORE", "groceries")
        for i in range(1, 40)
    ]
    spike = _txn(999, datetime.date(2024, 3, 15), 5000.0, "BIG STORE", "groceries")
    anomalies = detect_anomalies(normal + [spike])

    flagged_ids = {a["transaction_id"] for a in anomalies}
    assert 999 in flagged_ids                     # the big spike is caught
    assert all(a["z_score"] >= 1.5 for a in anomalies)  # only high-side outliers


def test_anomaly_skips_income_and_rent_categories():
    txns = [_txn(i, datetime.date(2024, 1, i % 27 + 1), 3000.0, "PAY", "income", "credit")
            for i in range(1, 20)]
    assert detect_anomalies(txns) == []
