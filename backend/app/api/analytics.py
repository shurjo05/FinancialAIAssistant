"""Aggregated analytics endpoints for the dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import tools

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    """Headline stats for the Overview page."""
    return tools.summary(db)


@router.get("/by-category")
def by_category(db: Session = Depends(get_db)) -> dict:
    """Total spending per category (for the donut / bar charts)."""
    return tools.get_spending_by_category(db)


@router.get("/monthly")
def monthly(db: Session = Depends(get_db)) -> list[dict]:
    """Spending and income per month (for the trend chart)."""
    return tools.monthly_trend(db)
