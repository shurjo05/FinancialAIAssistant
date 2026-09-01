"""Read endpoint for detected recurring subscriptions."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Subscription, User
from app.schemas.schemas import SubscriptionOut

router = APIRouter(prefix="/api", tags=["subscriptions"])


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    upload_id: int | None = None,
    kind: str | None = None,  # 'subscription' or 'bill'
) -> list[Subscription]:
    """Return this user's detected recurring payments, largest amount first.

    Filter by `kind` to split the "Subscriptions" tab (streaming/gym) from the
    "Recurring Payments" tab (rent/utilities/insurance).
    """
    query = (
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.amount.desc())
    )
    if upload_id is not None:
        query = query.where(Subscription.upload_id == upload_id)
    if kind is not None:
        query = query.where(Subscription.kind == kind)
    return list(db.scalars(query).all())
