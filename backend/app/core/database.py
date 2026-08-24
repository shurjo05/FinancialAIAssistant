"""
Database connection setup (SQLAlchemy 2.0 style).

Exposes three things the rest of the app uses:
  - `engine`     : the low-level connection to SQLite.
  - `SessionLocal`: a factory that hands out DB sessions (one per request).
  - `Base`       : the parent class every ORM model inherits from.
  - `get_db`     : a FastAPI dependency that yields a session and closes it.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# `check_same_thread=False` is required for SQLite under FastAPI (the
# connection may be touched from different threads). It is SQLite-specific,
# so only pass it for a SQLite URL — this keeps the code portable to Postgres.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)

# Each instance of SessionLocal() is a short-lived database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Parent class for all ORM models. SQLAlchemy 2.0 declarative base."""
    pass


def get_db():
    """FastAPI dependency: yield a session, always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
