"""Pydantic schemas: the request/response contract for the API.

These define exactly what the API accepts and returns as JSON, independent of
the SQLAlchemy models. `from_attributes=True` lets a schema be built directly
from an ORM object (e.g. TransactionOut.model_validate(transaction_row)).
"""

import datetime

from pydantic import BaseModel, ConfigDict


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
