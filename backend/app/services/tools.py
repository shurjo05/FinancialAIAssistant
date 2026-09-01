"""Data tools the AI layer and dashboard call to compute real numbers.

Every function is scoped to a single `user_id`, so a user can only ever see
their own data. Both the Gemini provider (via function-calling) and the
deterministic fallback call these same functions, so answers are always
grounded in the database.

Amount convention (from the parser): amount > 0 = expense, amount < 0 = income.
"""

import calendar
import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.models import Anomaly, Subscription, Transaction


def _parse_date(value: str | None) -> datetime.date | None:
    """Parse an ISO 'YYYY-MM-DD' string; return None if empty/invalid."""
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def month_bounds(month: str) -> tuple[datetime.date, datetime.date]:
    """Return (first_day, last_day) for a 'YYYY-MM' month string."""
    year, mon = (int(p) for p in month.split("-")[:2])
    last = calendar.monthrange(year, mon)[1]
    return datetime.date(year, mon, 1), datetime.date(year, mon, last)


def _expense_filters(user_id: int, start_date: str | None, end_date: str | None):
    """This user's expenses only, within an optional date range."""
    filters = [Transaction.user_id == user_id, Transaction.amount > 0]
    start, end = _parse_date(start_date), _parse_date(end_date)
    if start:
        filters.append(Transaction.date >= start)
    if end:
        filters.append(Transaction.date <= end)
    return filters


def date_range(db: Session, user_id: int) -> dict:
    """The user's min/max transaction date (context for resolving 'March')."""
    scope = Transaction.user_id == user_id
    lo = db.scalar(select(func.min(Transaction.date)).where(scope))
    hi = db.scalar(select(func.max(Transaction.date)).where(scope))
    return {"start": lo.isoformat() if lo else None, "end": hi.isoformat() if hi else None}


def get_spending_by_category(
    db: Session,
    user_id: int,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Total spending, optionally for one category and/or a date range."""
    filters = _expense_filters(user_id, start_date, end_date)
    if category:
        filters.append(Transaction.category == category)
        total = db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(*filters))
        count = db.scalar(select(func.count()).select_from(Transaction).where(*filters))
        return {"category": category, "total": round(total, 2), "count": count}

    rows = db.execute(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(*filters)
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()
    return {"by_category": {c: round(t, 2) for c, t in rows}}


def get_total(
    db: Session,
    user_id: int,
    kind: str = "spending",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Total 'spending' (money out) or 'income' (money in) over a date range."""
    start, end = _parse_date(start_date), _parse_date(end_date)
    scope = [Transaction.user_id == user_id]
    if start:
        scope.append(Transaction.date >= start)
    if end:
        scope.append(Transaction.date <= end)

    if kind == "income":
        total = db.scalar(
            select(func.coalesce(func.sum(-Transaction.amount), 0.0))
            .where(Transaction.amount < 0, *scope)
        )
    else:
        total = db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0.0))
            .where(Transaction.amount > 0, *scope)
        )
    return {"kind": kind, "total": round(total, 2)}


def top_merchants(
    db: Session,
    user_id: int,
    n: int = 5,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """The top merchants by total spend."""
    filters = _expense_filters(user_id, start_date, end_date)
    rows = db.execute(
        select(Transaction.merchant_normalized, func.sum(Transaction.amount))
        .where(*filters)
        .group_by(Transaction.merchant_normalized)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(n)
    ).all()
    return {"merchants": [{"merchant": m, "total": round(t, 2)} for m, t in rows]}


def compare_periods(
    db: Session, user_id: int, period_a: str, period_b: str, category: str | None = None
) -> dict:
    """Compare spending between two 'YYYY-MM' months, optionally for a category."""
    def spend(month: str) -> float:
        start, end = month_bounds(month)
        if category:
            return get_spending_by_category(
                db, user_id, category=category,
                start_date=start.isoformat(), end_date=end.isoformat(),
            ).get("total", 0.0)
        return get_total(db, user_id, "spending", start.isoformat(), end.isoformat())["total"]

    a, b = spend(period_a), spend(period_b)
    change = ((b - a) / a * 100) if a else None
    return {
        "category": category or "all",
        "period_a": period_a, "total_a": round(a, 2),
        "period_b": period_b, "total_b": round(b, 2),
        "change_pct": round(change, 1) if change is not None else None,
    }


def _recurring(db: Session, user_id: int, kind: str) -> dict:
    rows = db.scalars(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.kind == kind)
        .order_by(Subscription.amount.desc())
    ).all()
    monthly = sum(s.amount for s in rows if s.frequency == "monthly")
    return {
        "count": len(rows),
        "monthly_cost": round(monthly, 2),
        "annual_cost": round(monthly * 12, 2),
        "items": [
            {"merchant": s.merchant_normalized, "amount": s.amount,
             "frequency": s.frequency, "category": s.category}
            for s in rows
        ],
    }


def list_subscriptions(db: Session, user_id: int) -> dict:
    """Discretionary subscriptions (streaming, gym, software) + monthly/annual cost."""
    return _recurring(db, user_id, "subscription")


def list_recurring_bills(db: Session, user_id: int) -> dict:
    """Essential recurring bills (rent, utilities, insurance) + monthly/annual cost."""
    return _recurring(db, user_id, "bill")


def list_anomalies(db: Session, user_id: int) -> dict:
    """All flagged spending anomalies."""
    rows = db.scalars(
        select(Anomaly).where(Anomaly.user_id == user_id).order_by(Anomaly.z_score.desc())
    ).all()
    return {
        "count": len(rows),
        "anomalies": [
            {"type": a.anomaly_type, "category": a.category,
             "z_score": a.z_score, "description": a.description}
            for a in rows
        ],
    }


def monthly_trend(db: Session, user_id: int) -> list[dict]:
    """Spending and income totalled per calendar month (for the trend chart)."""
    # strftime is SQLite-specific; fine for this project's dev database.
    ym = func.strftime("%Y-%m", Transaction.date)
    rows = db.execute(
        select(
            ym.label("month"),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0.0)),
            func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0.0)),
        ).where(Transaction.user_id == user_id).group_by(ym).order_by(ym)
    ).all()
    return [{"month": m, "spending": round(s or 0, 2), "income": round(i or 0, 2)}
            for m, s, i in rows]


def summary(db: Session, user_id: int) -> dict:
    """Headline dashboard stats for one user."""
    total_spending = get_total(db, user_id, "spending")["total"]
    total_income = get_total(db, user_id, "income")["total"]
    net = round(total_income - total_spending, 2)
    savings_rate = round(net / total_income * 100, 1) if total_income else 0.0

    top = top_merchants(db, user_id, 1)["merchants"]
    largest = db.scalars(
        select(Transaction)
        .where(Transaction.user_id == user_id, Transaction.amount > 0)
        .order_by(Transaction.amount.desc()).limit(1)
    ).first()

    def count(model, *extra) -> int:
        return db.scalar(
            select(func.count()).select_from(model).where(model.user_id == user_id, *extra)
        ) or 0

    return {
        "total_spending": total_spending,
        "total_income": total_income,
        "net": net,
        "savings_rate": savings_rate,
        "transaction_count": count(Transaction),
        "subscription_count": count(Subscription, Subscription.kind == "subscription"),
        "bill_count": count(Subscription, Subscription.kind == "bill"),
        "anomaly_count": count(Anomaly),
        "top_merchant": top[0] if top else None,
        "largest_transaction": (
            {"merchant": largest.merchant_normalized, "amount": largest.amount,
             "category": largest.category, "date": largest.date.isoformat()}
            if largest else None
        ),
        "date_range": date_range(db, user_id),
    }
