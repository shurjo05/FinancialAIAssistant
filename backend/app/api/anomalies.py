"""Read endpoint for detected spending anomalies."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Anomaly
from app.schemas.schemas import AnomalyOut

router = APIRouter(prefix="/api", tags=["anomalies"])


@router.get("/anomalies", response_model=list[AnomalyOut])
def list_anomalies(
    db: Session = Depends(get_db),
    upload_id: int | None = None,
) -> list[Anomaly]:
    """Return detected anomalies, largest z-score first."""
    query = select(Anomaly).order_by(Anomaly.z_score.desc())
    if upload_id is not None:
        query = query.where(Anomaly.upload_id == upload_id)
    return list(db.scalars(query).all())
