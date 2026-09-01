"""Read endpoint for stored transactions, with pagination and filters."""

import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Transaction, User
from app.schemas.schemas import TransactionList, TransactionOut

router = APIRouter(prefix="/api", tags=["transactions"])


@router.get("/transactions", response_model=TransactionList)
def list_transactions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    upload_id: int | None = None,
    category: str | None = None,
    search: str | None = Query(None, description="merchant name contains"),
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
) -> TransactionList:
    """Return a filtered, paginated page of this user's transactions (newest first)."""
    filters = [Transaction.user_id == user.id]
    if upload_id is not None:
        filters.append(Transaction.upload_id == upload_id)
    if category:
        filters.append(Transaction.category == category)
    if search:
        filters.append(Transaction.merchant_normalized.ilike(f"%{search}%"))
    if date_from:
        filters.append(Transaction.date >= date_from)
    if date_to:
        filters.append(Transaction.date <= date_to)

    # Total matching rows (for the client to compute page count).
    total = db.scalar(select(func.count()).select_from(Transaction).where(*filters))

    rows = db.scalars(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return TransactionList(
        items=[TransactionOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
