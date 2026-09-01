"""Subscription and anomaly detection.

Two independent detectors run after an upload (as a background task):

  SubscriptionDetector - pure logic. Groups expenses by merchant, checks the
      charge cadence (interval buckets) and amount consistency to identify
      recurring payments.

  AnomalyDetector - ML (IsolationForest). Flags unusual transactions using
      per-category z-score, amount, merchant frequency, and day-of-month, with
      guardrails to avoid false positives on income/transfers/rent.
"""

import statistics
from collections import Counter, defaultdict

from sklearn.ensemble import IsolationForest
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models.models import Anomaly, Subscription, Transaction, Upload

# (target_days, tolerance, label) — a median interval within tolerance matches.
INTERVAL_BUCKETS = [
    (7, 2, "weekly"),
    (14, 3, "biweekly"),
    (30, 5, "monthly"),
    (90, 10, "quarterly"),
    (365, 20, "annual"),
]

# Amounts must be this consistent (coefficient of variation) to count as recurring.
MAX_AMOUNT_CV = 0.10

# Require at least this many charges before calling something recurring. Two
# points always form a "perfect" interval, so 2 is too weak (false positives
# like a pair of coincidentally-spaced Uber rides). 3 = real evidence.
MIN_OCCURRENCES = 3

# Essential recurring obligations -> shown as "bills", kept out of the
# "subscriptions" total so streaming/gym aren't lumped in with rent.
BILL_CATEGORIES = {"rent", "utilities", "fees", "insurance"}

# Anomaly guardrails: these categories are expected to be large/irregular, and
# tiny amounts are never worth flagging.
ANOMALY_SKIP_CATEGORIES = {"income", "transfers", "rent"}
ANOMALY_MIN_AMOUNT = 10.0
ANOMALY_CONTAMINATION = 0.05  # ~5% of eligible transactions flagged as candidates
# Only report high-side outliers: a spending anomaly means unusually HIGH spend,
# not a cheaper-than-usual purchase. Filters out negative-z false positives.
ANOMALY_MIN_ZSCORE = 1.5


def _match_interval(median_days: float) -> str | None:
    """Return the frequency label whose bucket contains the median interval."""
    for target, tolerance, label in INTERVAL_BUCKETS:
        if abs(median_days - target) <= tolerance:
            return label
    return None


def detect_subscriptions(
    transactions: list[Transaction],
) -> tuple[list[dict], set[int]]:
    """Find recurring payments.

    Returns (subscription_records, recurring_transaction_ids). A group qualifies
    when it has >=2 charges, a regular interval, and consistent amounts.
    """
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.amount and t.amount > 0:  # expenses only
            groups[t.merchant_normalized].append(t)

    subscriptions: list[dict] = []
    recurring_ids: set[int] = set()

    for merchant, txns in groups.items():
        if len(txns) < MIN_OCCURRENCES:
            continue

        txns.sort(key=lambda t: t.date)
        intervals = [(txns[i + 1].date - txns[i].date).days for i in range(len(txns) - 1)]
        frequency = _match_interval(statistics.median(intervals))
        if frequency is None:
            continue

        amounts = [t.amount for t in txns]
        mean_amount = statistics.mean(amounts)
        if mean_amount <= 0:
            continue
        cv = statistics.pstdev(amounts) / mean_amount if len(amounts) > 1 else 0.0
        if cv > MAX_AMOUNT_CV:
            continue

        category = Counter(t.category for t in txns).most_common(1)[0][0]
        kind = "bill" if category in BILL_CATEGORIES else "subscription"

        subscriptions.append({
            "merchant_normalized": merchant,
            "amount": round(mean_amount, 2),
            "frequency": frequency,
            "last_charged": max(t.date for t in txns),
            "occurrence_count": len(txns),
            "total_spent": round(sum(amounts), 2),
            "category": category,
            "kind": kind,
        })
        recurring_ids.update(t.id for t in txns)

    return subscriptions, recurring_ids


def detect_anomalies(transactions: list[Transaction]) -> list[dict]:
    """Flag unusual transactions with IsolationForest.

    Features: amount, per-category z-score, merchant frequency, day-of-month.
    Returns anomaly records keyed to transaction ids.
    """
    candidates = [
        t for t in transactions
        if t.amount and t.amount >= ANOMALY_MIN_AMOUNT
        and t.category not in ANOMALY_SKIP_CATEGORIES
    ]
    if len(candidates) < 10:  # too few to model meaningfully
        return []

    # Per-category amount stats for the z-score feature.
    cat_amounts: dict[str, list[float]] = defaultdict(list)
    for t in candidates:
        cat_amounts[t.category].append(t.amount)
    cat_stats = {
        c: (statistics.mean(a), statistics.pstdev(a) if len(a) > 1 else 0.0)
        for c, a in cat_amounts.items()
    }

    merchant_freq = Counter(t.merchant_normalized for t in transactions)

    def zscore(t: Transaction) -> float:
        mean, std = cat_stats[t.category]
        return (t.amount - mean) / std if std > 0 else 0.0

    features = [
        [t.amount, zscore(t), merchant_freq[t.merchant_normalized], t.date.day]
        for t in candidates
    ]

    model = IsolationForest(contamination=ANOMALY_CONTAMINATION, random_state=42)
    predictions = model.fit_predict(features)

    anomalies: list[dict] = []
    for t, prediction in zip(candidates, predictions, strict=False):
        if prediction != -1:
            continue
        z = zscore(t)
        if z < ANOMALY_MIN_ZSCORE:
            continue  # only flag unusually HIGH spend, not low-value outliers
        anomaly_type = "large_single" if z > 2 else "spike"
        anomalies.append({
            "transaction_id": t.id,
            "anomaly_type": anomaly_type,
            "z_score": round(z, 2),
            "category": t.category,
            "description": (
                f"{t.merchant_normalized} charge of ${t.amount:,.2f} is unusual "
                f"for {t.category} (z-score {z:.1f})"
            ),
        })
    return anomalies


def run_detectors(upload_id: int) -> None:
    """Background task: run both detectors for an upload and persist results.

    Opens its own session because the request's session is already closed by
    the time this runs. Idempotent: clears prior results for the upload first.
    """
    db = SessionLocal()
    try:
        upload = db.get(Upload, upload_id)
        if upload is None:
            return
        user_id = upload.user_id

        transactions = db.scalars(
            select(Transaction).where(Transaction.upload_id == upload_id)
        ).all()
        if not transactions:
            return

        subscriptions, recurring_ids = detect_subscriptions(transactions)
        anomalies = detect_anomalies(transactions)
        anomaly_ids = {a["transaction_id"] for a in anomalies}

        # Idempotency: remove any previous detector output for this upload.
        db.execute(delete(Subscription).where(Subscription.upload_id == upload_id))
        db.execute(delete(Anomaly).where(Anomaly.upload_id == upload_id))

        for record in subscriptions:
            db.add(Subscription(upload_id=upload_id, user_id=user_id, **record))
        for record in anomalies:
            db.add(Anomaly(upload_id=upload_id, user_id=user_id, **record))

        for t in transactions:
            t.is_recurring = t.id in recurring_ids
            t.is_anomaly = t.id in anomaly_ids

        db.commit()
    finally:
        db.close()
