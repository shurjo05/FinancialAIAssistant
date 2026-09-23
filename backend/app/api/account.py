"""Account management endpoints (e.g. clearing your own data)."""

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import (
    Anomaly,
    Conversation,
    Correction,
    Message,
    MonthlySummary,
    PlaidItem,
    Subscription,
    Transaction,
    Upload,
    User,
)
from app.schemas.schemas import ClearDataResult

router = APIRouter(prefix="/api/account", tags=["account"])


@router.post("/clear-data", response_model=ClearDataResult)
def clear_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClearDataResult:
    """Delete ALL of this user's ingested data. Keeps the account and login.

    Removes uploads/transactions (CSV + Plaid), detector output, corrections,
    bank connections, and chat threads. Scoped strictly to the current user.
    """
    tx_count = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.user_id == user.id)
    ) or 0

    upload_ids = select(Upload.id).where(Upload.user_id == user.id)
    conversation_ids = select(Conversation.id).where(Conversation.user_id == user.id)

    # Delete children before parents so it works on Postgres (FK-enforced) and
    # SQLite (a bulk DELETE doesn't cascade) alike.
    db.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
    db.execute(delete(Conversation).where(Conversation.user_id == user.id))
    db.execute(delete(Anomaly).where(Anomaly.user_id == user.id))
    db.execute(delete(Correction).where(Correction.user_id == user.id))
    db.execute(delete(MonthlySummary).where(MonthlySummary.upload_id.in_(upload_ids)))
    db.execute(delete(Subscription).where(Subscription.user_id == user.id))
    db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    db.execute(delete(Upload).where(Upload.user_id == user.id))
    db.execute(delete(PlaidItem).where(PlaidItem.user_id == user.id))
    db.commit()

    return ClearDataResult(transactions_deleted=tx_count)
