"""Correction history: the user's category corrections (audit + training signal)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Correction, User
from app.schemas.schemas import CorrectionOut

router = APIRouter(prefix="/api", tags=["corrections"])


@router.get("/corrections", response_model=list[CorrectionOut])
def list_corrections(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CorrectionOut]:
    """This user's category corrections, newest first (exportable for retraining)."""
    rows = db.scalars(
        select(Correction)
        .where(Correction.user_id == user.id)
        .order_by(Correction.created_at.desc(), Correction.id.desc())
    ).all()
    return [CorrectionOut.model_validate(r) for r in rows]
