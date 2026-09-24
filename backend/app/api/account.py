"""Account endpoints: balances of connected bank accounts, and clearing your own data."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.auth import DEMO_EMAIL
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import (
    Account,
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
from app.schemas.schemas import AccountBalances, ClearDataResult
from app.services import tools

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("/balances", response_model=AccountBalances)
def balances(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountBalances:
    """Connected accounts with their latest balances, plus net worth.

    Same computation Jo's `account_balances` tool uses, so the dashboard and the
    chat can never disagree.
    """
    connected = db.scalar(select(PlaidItem.id).where(PlaidItem.user_id == user.id)) is not None
    return AccountBalances.model_validate(
        {**tools.account_balances(db, user.id), "bank_connected": connected}
    )


@router.post("/clear-data", response_model=ClearDataResult)
def clear_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ClearDataResult:
    """Delete ALL of this user's ingested data. Keeps the account and login.

    Removes uploads/transactions (CSV + Plaid), detector output, corrections,
    bank connections, and chat threads. Scoped strictly to the current user.
    """
    if user.email == DEMO_EMAIL:
        # Shared account: clearing it would empty the demo for every visitor.
        raise HTTPException(status_code=403, detail="The shared demo's data can't be cleared.")

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
    db.execute(delete(Account).where(Account.user_id == user.id))
    db.commit()

    return ClearDataResult(transactions_deleted=tx_count)
