"""Natural-language query endpoint (agentic, grounded, scoped to the user)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import User
from app.schemas.schemas import QueryRequest, QueryResponse
from app.services.ai_service import answer_query

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QueryResponse:
    """Answer a plain-English question using this user's data (Gemini or fallback)."""
    result = answer_query(db, user.id, payload.question)
    return QueryResponse(**result)
