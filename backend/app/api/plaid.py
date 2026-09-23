"""Plaid "connect a bank" endpoints (sandbox, per-user, feature-flagged).

Flow: link-token -> (frontend Link widget) -> exchange -> sync. All require auth
and a configured Plaid (503 otherwise). The access token is stored Fernet-
ENCRYPTED and decrypted just-in-time. Sandbox only: fake institutions, test login
user_good / pass_good — never real bank credentials.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.upload import persist_rows
from app.core.config import settings
from app.core.crypto import decrypt, encrypt
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logging import get_logger
from app.models.models import PlaidItem, User
from app.schemas.schemas import (
    LinkTokenOut,
    PlaidExchangeRequest,
    PlaidItemOut,
    PlaidStatus,
    PlaidSyncResult,
)
from app.services import plaid_client
from app.services.accounts import replace_plaid_accounts

logger = get_logger("app.plaid")

router = APIRouter(prefix="/api/plaid", tags=["plaid"])


def _require_plaid() -> None:
    if not settings.plaid_configured:
        raise HTTPException(status_code=503, detail="Bank connections aren't configured on this server.")


def _refresh_accounts(db: Session, user_id: int, access_token: str, institution: str | None) -> None:
    """Pull the latest balances. Best-effort: a failure here never blocks a sync."""
    try:
        accounts = plaid_client.get_accounts(access_token)
    except Exception:
        logger.warning("could not refresh plaid account balances")
        return
    replace_plaid_accounts(db, user_id, institution, accounts)


@router.get("/status", response_model=PlaidStatus)
def plaid_status(user: User = Depends(get_current_user)) -> PlaidStatus:
    """Whether the connect-a-bank feature is available (frontend shows/hides the button)."""
    return PlaidStatus(configured=settings.plaid_configured)


@router.post("/link-token", response_model=LinkTokenOut)
def link_token(user: User = Depends(get_current_user)) -> LinkTokenOut:
    """Create a Link token to open the Plaid widget."""
    _require_plaid()
    return LinkTokenOut(link_token=plaid_client.create_link_token(user.id))


@router.post("/exchange", response_model=PlaidItemOut)
def exchange(
    payload: PlaidExchangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlaidItemOut:
    """Exchange the Link public_token for an access token; store the item (single per user)."""
    _require_plaid()
    item_id, access_token = plaid_client.exchange_public_token(payload.public_token)
    institution = plaid_client.get_institution_name(access_token)

    # Single item per user: replace any existing connection.
    item = db.scalar(select(PlaidItem).where(PlaidItem.user_id == user.id))
    if item is None:
        item = PlaidItem(user_id=user.id)
        db.add(item)
    item.item_id = item_id
    item.access_token = encrypt(access_token)  # encrypted at rest
    item.institution_name = institution
    item.cursor = None                         # start a fresh sync
    _refresh_accounts(db, user.id, access_token, institution)
    db.commit()
    return PlaidItemOut(item_id=item_id, institution_name=institution)


@router.post("/sync", response_model=PlaidSyncResult)
def sync(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PlaidSyncResult:
    """Pull new transactions for this user's connected bank into the dashboard."""
    _require_plaid()
    item = db.scalar(select(PlaidItem).where(PlaidItem.user_id == user.id))
    if item is None:
        raise HTTPException(status_code=404, detail="No connected bank. Connect one first.")

    access_token = decrypt(item.access_token)
    rows, next_cursor = plaid_client.sync_transactions(access_token, item.cursor)
    item.cursor = next_cursor
    _refresh_accounts(db, user.id, access_token, item.institution_name)
    if rows:
        # persist_rows commits (transactions + the cursor change); else commit the cursor alone.
        persist_rows(db, background_tasks, user.id, item.institution_name or "Plaid", rows, source="plaid")
    else:
        db.commit()
    return PlaidSyncResult(added=len(rows), institution_name=item.institution_name)
