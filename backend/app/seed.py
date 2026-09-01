"""Dev-only seed: create a demo account and load the sample data for it.

Guarded to run only against a local SQLite database (or when ALLOW_DEMO_SEED is
set) so a known-password account is never seeded into production.

Run (from backend/, after `alembic upgrade head`):
    python -m app.seed
Then log in with the credentials it prints.
"""

import asyncio
import os

from fastapi import BackgroundTasks
from sqlalchemy import func, select

from app.api.upload import SAMPLE_CSV, _ingest
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import Transaction, User

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"


def _seeding_allowed() -> bool:
    return settings.database_url.startswith("sqlite") or bool(os.getenv("ALLOW_DEMO_SEED"))


def main() -> None:
    if not _seeding_allowed():
        print(
            "Refusing to seed: this is not a local SQLite database. "
            "Set ALLOW_DEMO_SEED=1 to override (never do this in production)."
        )
        return

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            print(f"Demo user already exists: {DEMO_EMAIL} / {DEMO_PASSWORD}")

        # Load sample data only if this user has none yet (idempotent / self-healing).
        existing = db.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.user_id == user.id)
        )
        if existing:
            print(f"User already has {existing} transactions; skipping sample load.")
            return

        background = BackgroundTasks()
        text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
        result = _ingest(db, background, user.id, "sample_transactions.csv", text)
        asyncio.run(background())  # run the detector task now instead of later
        print(f"Loaded {result.row_count} sample transactions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
