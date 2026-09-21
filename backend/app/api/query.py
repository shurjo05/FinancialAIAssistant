"""Stateless natural-language query endpoint (agentic, grounded, per-user).

This is the ephemeral chat path: it persists nothing and is what the shared demo
account uses. Conversation memory here is client-supplied via `history` (bounded
again server-side). Authenticated real users get durable threads via
`/api/conversations/messages` instead. Because the demo funnels through one
shared account, the per-minute limit here caps all demo traffic combined; the
real budget guard is the per-day Gemini cap (see ai_service).
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import limiter, user_or_ip
from app.models.models import User
from app.schemas.schemas import QueryRequest, QueryResponse
from app.services.ai_service import answer_query
from app.services.chat import build_context

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute", key_func=user_or_ip)
def query(
    request: Request,
    payload: QueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QueryResponse:
    """Answer a plain-English question using this user's data (Gemini or fallback)."""
    history = build_context([turn.model_dump() for turn in payload.history])
    result = answer_query(db, user.id, payload.question, history=history, style=payload.style)
    return QueryResponse(**result)
