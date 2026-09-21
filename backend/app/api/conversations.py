"""Persisted chat threads with Jo (authenticated real users only).

The shared demo account is intentionally excluded — it uses the stateless
`/api/query` path and persists nothing. Real users get durable, resumable
threads here; only a bounded recent window of each thread is sent to the model.
"""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import DEMO_EMAIL
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import limiter, user_or_ip
from app.models.models import Conversation, Message, User
from app.schemas.schemas import (
    ConversationDetail,
    ConversationOut,
    MessageCreate,
    MessageOut,
    SendResult,
)
from app.services.ai_service import answer_query
from app.services.chat import build_context

router = APIRouter(prefix="/api", tags=["conversations"])

# Newest N threads kept per user; older ones are auto-pruned. Housekeeping only —
# it never affects what the model sees (that's the per-request context window).
MAX_CONVERSATIONS_PER_USER = 50
_TITLE_MAX = 60


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _forbid_demo(user: User) -> None:
    """The demo account has no persistence; it must use the stateless chat path."""
    if user.email == DEMO_EMAIL:
        raise HTTPException(status_code=403, detail="The demo uses an in-session chat that isn't saved.")


def _get_owned(db: Session, user: User, conversation_id: int) -> Conversation:
    conv = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    if conv is None:
        # 404 (not 403) so we don't reveal that someone else's id exists.
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv


def _prune(db: Session, user_id: int) -> None:
    overflow = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(MAX_CONVERSATIONS_PER_USER)
    ).all()
    for conv in overflow:  # ORM cascade removes each thread's messages
        db.delete(conv)


@router.post("/conversations/messages", response_model=SendResult)
@limiter.limit("30/minute", key_func=user_or_ip)
def send_message(
    request: Request,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SendResult:
    """Ask Jo within a thread. Omit `conversation_id` to start a new one."""
    _forbid_demo(user)

    # Resolve the thread + its history BEFORE answering, and write nothing until
    # the answer succeeds — so a transient AI failure (503) leaves no half-saved
    # turn and no empty conversation.
    existing = payload.conversation_id is not None
    conv = _get_owned(db, user, payload.conversation_id) if existing else None
    prior = (
        db.scalars(
            select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at)
        ).all()
        if conv
        else []
    )
    history = build_context([{"role": m.role, "content": m.content} for m in prior])

    # May raise AIUnavailable -> 503 (retryable); nothing has been written yet.
    result = answer_query(db, user.id, payload.question, history=history, style=payload.style)

    if conv is None:
        conv = Conversation(user_id=user.id, title=payload.question[:_TITLE_MAX])
        db.add(conv)
        db.flush()  # assign conv.id
        _prune(db, user.id)

    # Persist both turns now that we have a real answer.
    db.add(Message(conversation_id=conv.id, role="user", content=payload.question))
    assistant = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["answer"],
        tools_used=result.get("tools_used") or [],
        provider=result.get("provider"),
    )
    db.add(assistant)
    conv.updated_at = _utcnow()  # bump so the thread sorts to the top of the list
    db.commit()
    db.refresh(assistant)

    return SendResult(
        conversation_id=conv.id,
        title=conv.title,
        message=MessageOut.model_validate(assistant),
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Conversation]:
    """This user's threads, most-recently-active first."""
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
        ).all()
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    """Fetch one thread with its full message history (to resume it)."""
    return _get_owned(db, user, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete a thread and all its messages."""
    conv = _get_owned(db, user, conversation_id)
    db.delete(conv)
    db.commit()
