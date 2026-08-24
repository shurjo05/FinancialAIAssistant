"""SQLAlchemy ORM models for the Personal Finance AI Assistant.

Each class maps to one SQLite table. Columns use the SQLAlchemy 2.0 typed
style: ``Mapped[type]`` annotations paired with ``mapped_column(...)``. A
``Mapped[str]`` is NOT NULL by default; ``Mapped[str | None]`` is nullable.

Amount sign convention (see cleaner/parser): positive = expense, negative =
income. This is normalized on ingest so all downstream analysis is consistent.
"""

import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Upload(Base):
    """A single CSV import. Parent of every transaction it produced."""

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    # Timestamp is populated by the database on insert.
    uploaded_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    row_count: Mapped[int] = mapped_column(default=0)
    date_range_start: Mapped[datetime.date | None]
    date_range_end: Mapped[datetime.date | None]
    status: Mapped[str] = mapped_column(default="processing")

    # Deleting an upload cascades to its transactions (orphan cleanup).
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan"
    )


class Transaction(Base):
    """A normalized transaction row: cleaned, categorized, and flagged."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
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
    merchant_normalized: Mapped[str]
    amount: Mapped[float]                 # typical charge amount
    frequency: Mapped[str]               # 'weekly' | 'monthly' | 'annual' | ...
    last_charged: Mapped[datetime.date]
    occurrence_count: Mapped[int]
    total_spent: Mapped[float]


class Anomaly(Base):
    """An unusual transaction or spending spike flagged by the detector."""

    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    anomaly_type: Mapped[str]            # 'spike' | 'unusual_merchant' | 'large_single'
    z_score: Mapped[float | None]        # null for methods that don't produce one (e.g. IQR)
    category: Mapped[str]
    description: Mapped[str]             # human-readable explanation


class MonthlySummary(Base):
    """Pre-aggregated spend per category per month, for fast dashboards."""

    __tablename__ = "monthly_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"))
    year_month: Mapped[str]              # e.g. '2024-03'
    category: Mapped[str]
    total_spent: Mapped[float]
    transaction_count: Mapped[int]
