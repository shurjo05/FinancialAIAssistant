"""Read endpoint for stored transactions, with pagination and filters."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.metrics import metrics
from app.models.models import Correction, Transaction, User
from app.schemas.schemas import CategoryUpdate, TransactionList, TransactionOut
from app.services.categorizer import CATEGORIES, CONFIDENCE_THRESHOLD, model_info

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
    low_confidence: bool = Query(False, description="only rows the model was unsure about"),
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
    if low_confidence:
        # Active-learning queue: predictions the model was least sure about.
        filters.append(Transaction.category_confidence < CONFIDENCE_THRESHOLD)

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


@router.patch("/transactions/{transaction_id}/category", response_model=TransactionOut)
def correct_category(
    transaction_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TransactionOut:
    """Correct a transaction's category and record it as training signal."""
    txn = db.get(Transaction, transaction_id)
    if txn is None or txn.user_id != user.id:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    new_category = payload.category
    if new_category not in CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Unknown category: {new_category!r}")

    if new_category != txn.category:
        # Audit + training signal: what the model predicted, at what confidence,
        # on which model version — before we overwrite it with the human label.
        db.add(Correction(
            user_id=user.id,
            transaction_id=txn.id,
            original_category=txn.category,
            corrected_category=new_category,
            original_confidence=txn.category_confidence,
            model_version=model_info().get("model_version"),
        ))
        txn.category = new_category
        txn.category_confidence = 1.0  # human ground truth
        db.commit()
        db.refresh(txn)
        metrics.incr("category_corrections_total")

    return TransactionOut.model_validate(txn)
