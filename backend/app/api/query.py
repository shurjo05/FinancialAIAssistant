"""Natural-language query endpoint (agentic, grounded in the data)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.schemas import QueryRequest, QueryResponse
from app.services.ai_service import answer_query

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    """Answer a plain-English question using computed data (Gemini or fallback)."""
    result = answer_query(db, payload.question)
    return QueryResponse(**result)
