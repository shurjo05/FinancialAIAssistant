"""SQLAlchemy ORM models for the Personal Finance AI Assistant.

Each class maps to one SQLite table. Columns use the SQLAlchemy 2.0 typed
style: ``Mapped[type]`` annotations paired with ``mapped_column(...)``. A
``Mapped[str]`` is NOT NULL by default; ``Mapped[str | None]`` is nullable.

Amount sign convention (see cleaner/parser): positive = expense, negative =
income. This is normalized on ingest so all downstream analysis is consistent.
"""

import datetime

from sqlalchemy import JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """An account. Owns uploads and all data derived from them."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    # Bumped to revoke all of this user's tokens at once (logout-all, password
    # change). A token is valid only while its `ver` claim matches this.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")


class Upload(Base):
    """A single ingest batch (a CSV import or a Plaid sync). Parent of its transactions."""

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str]
    # Timestamp is populated by the database on insert.
    uploaded_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    row_count: Mapped[int] = mapped_column(default=0)
    date_range_start: Mapped[datetime.date | None]
    date_range_end: Mapped[datetime.date | None]
    status: Mapped[str] = mapped_column(default="processing")
    # Where the rows came from: 'csv' or 'plaid'.
    source: Mapped[str] = mapped_column(default="csv", server_default="csv")

    # Deleting an upload cascades to its transactions (orphan cleanup).
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )


class PlaidItem(Base):
    """A user's connection to one institution via Plaid (sandbox).

    One row per connected bank; we keep a single item per user for now. The
    `access_token` is stored Fernet-ENCRYPTED (never plaintext) and decrypted
    just-in-time to call Plaid. `cursor` tracks incremental /transactions/sync.
    """

    __tablename__ = "plaid_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ondelete declared to match the migration (keeps `alembic check` green).
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str] = mapped_column(unique=True, index=True)  # Plaid's item id
    access_token: Mapped[str]                # Fernet-encrypted at rest
    institution_name: Mapped[str | None]
    cursor: Mapped[str | None]               # /transactions/sync incremental cursor
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Transaction(Base):
    """A normalized transaction row: cleaned, categorized, and flagged."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[datetime.date]
    description: Mapped[str]              # raw merchant string from the CSV
    merchant_normalized: Mapped[str]     # cleaned merchant name
    amount: Mapped[float]                # positive = expense, negative = income
    transaction_type: Mapped[str]        # 'debit' or 'credit'
    category: Mapped[str]
    category_confidence: Mapped[float]   # 0.0-1.0, from the categorizer
    # Set by the background detectors after ingest.
    is_recurring: Mapped[bool] = mapped_column(default=False)
    is_anomaly: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None]            # user-editable (stretch)

    upload: Mapped["Upload"] = relationship(back_populates="transactions")


class Subscription(Base):
    """A recurring payment inferred by the subscription detector."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_normalized: Mapped[str]
    amount: Mapped[float]                 # typical charge amount
    frequency: Mapped[str]               # 'weekly' | 'monthly' | 'annual' | ...
    last_charged: Mapped[datetime.date]
    occurrence_count: Mapped[int]
    total_spent: Mapped[float]
    category: Mapped[str] = mapped_column(default="other")
    kind: Mapped[str] = mapped_column(default="subscription")  # 'subscription' | 'bill'


class Anomaly(Base):
    """An unusual transaction or spending spike flagged by the detector."""

    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    anomaly_type: Mapped[str]            # 'spike' | 'unusual_merchant' | 'large_single'
    z_score: Mapped[float | None]        # null for methods that don't produce one (e.g. IQR)
    category: Mapped[str]
    description: Mapped[str]             # human-readable explanation


class Correction(Base):
    """A user's category correction: training signal + prediction audit trail.

    Records what the model predicted, what the human changed it to, the model's
    original confidence, and which model version made the prediction — so
    corrections can be exported and fed into a (manual, gated) retrain later.
    """

    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    original_category: Mapped[str]
    corrected_category: Mapped[str]
    original_confidence: Mapped[float]
    model_version: Mapped[str | None]  # from model_metadata.json; None if rules-only
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Conversation(Base):
    """A saved chat thread between a user and Jo.

    Only authenticated real users get persisted conversations; the shared demo
    account uses a stateless in-session chat (nothing written here). History is
    stored in full, but only a bounded recent window is ever sent to the LLM.
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ondelete matches the migration's DB-level cascade (keeps model ↔ migration in
    # sync for `alembic check`); the relationship cascade below handles ORM deletes.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str]                    # derived from the first question
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    # Bumped on every new message, so the conversation list sorts most-recent-first.
    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Deleting a conversation (or its owner) cascades to its messages.
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """One turn in a conversation: a user question or Jo's answer."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str]                     # 'user' | 'assistant'
    content: Mapped[str]
    # Assistant turns only: which tools Jo called and which provider answered —
    # the same transparency we surface on the live query response.
    tools_used: Mapped[list | None] = mapped_column(JSON, default=None)
    provider: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class MonthlySummary(Base):
    """Pre-aggregated spend per category per month, for fast dashboards."""

    __tablename__ = "monthly_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    year_month: Mapped[str]              # e.g. '2024-03'
    category: Mapped[str]
    total_spent: Mapped[float]
    transaction_count: Mapped[int]
