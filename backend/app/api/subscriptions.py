"""Read endpoint for detected recurring subscriptions."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Subscription
from app.schemas.schemas import SubscriptionOut

router = APIRouter(prefix="/api", tags=["subscriptions"])


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def list_subscriptions(
    db: Session = Depends(get_db),
    upload_id: int | None = None,
    kind: str | None = None,  # 'subscription' or 'bill'
) -> list[Subscription]:
    """Return detected recurring payments, largest amount first.

    Filter by `kind` to split the "Subscriptions" tab (streaming/gym) from the
    "Recurring Payments" tab (rent/utilities/insurance).
    """
    query = select(Subscription).order_by(Subscription.amount.desc())
    if upload_id is not None:
        query = query.where(Subscription.upload_id == upload_id)
    if kind is not None:
        query = query.where(Subscription.kind == kind)
    return list(db.scalars(query).all())
