"""Shared pytest fixtures.

Points the whole app at an isolated temp SQLite database and forces the
rule-based AI path (no network) by setting env vars BEFORE the app is imported.
Tables are wiped between tests for isolation.
"""

import os
import tempfile
from pathlib import Path

# Must run before any `app.*` import so settings bind to the test DB.
_TMP_DIR = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"
os.environ["GOOGLE_API_KEY"] = ""  # force deterministic rule-based query path

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """Wipe all tables after each test so tests don't leak state into each other."""
    yield
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_csv() -> str:
    return str(DATA_DIR / "chase_sample.csv")
