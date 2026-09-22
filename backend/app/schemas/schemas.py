"""Pydantic schemas: the request/response contract for the API.

These define exactly what the API accepts and returns as JSON, independent of
the SQLAlchemy models. `from_attributes=True` lets a schema be built directly
from an ORM object (e.g. TransactionOut.model_validate(transaction_row)).
"""

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Registration / login payload."""

    email: EmailStr
    password: str
    # Cloudflare Turnstile token from the widget; required only when CAPTCHA is
    # configured (verified server-side, then discarded — never stored).
    turnstile_token: str | None = None


class PasswordChange(BaseModel):
    """Change-password payload."""

    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    """A user as returned by the API (never includes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class Token(BaseModel):
    """A JWT access token."""

    access_token: str
    token_type: str = "bearer"


class ParseError(BaseModel):
    """One row that could not be parsed, surfaced to the client."""

    row: int
    issue: str
    raw: str


class UploadResult(BaseModel):
    """Summary returned after a CSV upload is processed."""

    upload_id: int
    filename: str
    row_count: int
    error_count: int
    date_range_start: datetime.date | None = None
    date_range_end: datetime.date | None = None
    status: str
    errors: list[ParseError] = []


class TransactionOut(BaseModel):
    """A single transaction as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    upload_id: int
    date: datetime.date
    description: str
    merchant_normalized: str
    amount: float
    transaction_type: str
    category: str
    category_confidence: float
    is_recurring: bool
    is_anomaly: bool


class TransactionList(BaseModel):
    """A paginated page of transactions."""

    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class CategoryUpdate(BaseModel):
    """Body for correcting a transaction's category."""

    category: str


class CorrectionOut(BaseModel):
    """A recorded category correction (training signal + audit)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    original_category: str
    corrected_category: str
    original_confidence: float
    model_version: str | None
    created_at: datetime.datetime


class SubscriptionOut(BaseModel):
    """A detected recurring payment."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    upload_id: int
    merchant_normalized: str
    amount: float
    frequency: str
    last_charged: datetime.date
    occurrence_count: int
    total_spent: float
    category: str
    kind: str


class AnomalyOut(BaseModel):
    """A flagged unusual transaction."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    upload_id: int
    transaction_id: int
    anomaly_type: str
    z_score: float | None
    category: str
    description: str


ChatStyle = Literal["friendly", "numbers", "coach"]


class ChatTurn(BaseModel):
    """One prior turn, supplied by the client for the stateless (demo) chat path."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class QueryRequest(BaseModel):
    """A natural-language question about the user's finances (stateless path).

    `history` carries prior turns for the demo chat (which persists nothing);
    it is bounded again server-side before reaching the model.
    """

    question: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = Field(default=[], max_length=50)
    style: ChatStyle = "friendly"


class QueryResponse(BaseModel):
    """The grounded answer plus which provider and tools produced it."""

    answer: str
    provider: str
    tools_used: list[str] = []


class MessageOut(BaseModel):
    """One stored turn in a persisted conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    tools_used: list[str] | None = None
    provider: str | None = None
    created_at: datetime.datetime


class ConversationOut(BaseModel):
    """A conversation in the user's thread list (no messages)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ConversationDetail(ConversationOut):
    """A conversation with its full message history (for resuming a thread)."""

    messages: list[MessageOut] = []


class MessageCreate(BaseModel):
    """Send a message. Omit `conversation_id` to start a new thread."""

    conversation_id: int | None = None
    question: str = Field(min_length=1, max_length=500)
    style: ChatStyle = "friendly"


class SendResult(BaseModel):
    """The result of sending a message: Jo's reply plus the (maybe new) thread."""

    conversation_id: int
    title: str
    message: MessageOut
