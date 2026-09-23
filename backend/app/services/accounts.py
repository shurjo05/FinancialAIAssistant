"""Writing account balances: from Plaid, or synthetic ones for the demo.

Reading/totalling lives in tools.account_balances, so the dashboard and Jo share
one computation.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.models import Account

# Synthetic accounts for the shared demo, so the demo path shows balances.
# Always stored as source='sample' and labeled "Sample" in the UI and to Jo.
SAMPLE_ACCOUNTS = (
    {"name": "Everyday Checking", "mask": "4821", "type": "depository",
     "subtype": "checking", "current_balance": 3842.17, "available_balance": 3792.17},
    {"name": "High-Yield Savings", "mask": "9035", "type": "depository",
     "subtype": "savings", "current_balance": 11250.00, "available_balance": 11250.00},
    {"name": "Rewards Credit Card", "mask": "6107", "type": "credit",
     "subtype": "credit card", "current_balance": 1286.43, "available_balance": 6213.57},
)


def replace_plaid_accounts(
    db: Session, user_id: int, institution: str | None, accounts: list[dict]
) -> None:
    """Swap in the latest Plaid accounts for this user (single item → full replace).

    Caller commits. Replacing wholesale keeps it correct when an item is swapped
    for a different bank, and nothing references account rows by id.
    """
    db.execute(delete(Account).where(Account.user_id == user_id, Account.source == "plaid"))
    db.add_all(
        Account(user_id=user_id, source="plaid", institution_name=institution, **a)
        for a in accounts
    )


def seed_sample_accounts(db: Session, user_id: int) -> None:
    """Give an account the synthetic demo balances, once. Caller commits."""
    has_any = db.scalar(
        select(func.count()).select_from(Account).where(Account.user_id == user_id)
    )
    if has_any:
        return
    db.add_all(
        Account(user_id=user_id, source="sample", institution_name="Sample Bank", **a)
        for a in SAMPLE_ACCOUNTS
    )
