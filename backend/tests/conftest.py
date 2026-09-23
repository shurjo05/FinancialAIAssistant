"""Shared pytest fixtures.

Points the whole app at an isolated temp SQLite database and forces the
rule-based AI path (no network) by setting env vars BEFORE the app is imported.
Tables are wiped between tests for isolation.
"""

import os
import tempfile
from pathlib import Path

# Must run before any `app.*` import so settings bind to the test DB.
# Default: an isolated temp SQLite DB — fast, zero-setup inner loop.
# Override with TEST_DATABASE_URL (e.g. a Postgres container) to run the same
# suite against another backend and prove dialect portability.
_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")
if not _TEST_DB_URL:
    _TMP_DIR = tempfile.mkdtemp()
    _TEST_DB_URL = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"
os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ["GOOGLE_API_KEY"] = ""  # force deterministic rule-based query path
# Neutralize optional feature keys so a developer's local .env can't change test
# behavior (env vars take precedence over .env in pydantic-settings): CAPTCHA off
# and Plaid off by default, matching CI where no .env exists.
os.environ["TURNSTILE_SECRET"] = ""
os.environ["PLAID_CLIENT_ID"] = ""
os.environ["PLAID_SECRET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.ratelimit import limiter  # noqa: E402
from app.main import app  # noqa: E402

# Rate limiting off by default so auth fixtures can log in freely; the dedicated
# rate-limit test enables it locally.
limiter.enabled = False

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


@pytest.fixture
def user(db):
    """A persisted user, for tests that call user-scoped services directly."""
    from app.core.security import hash_password
    from app.models.models import User

    u = User(email="direct@example.com", hashed_password=hash_password("Pw12345!"))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def auth_token(client):
    """Factory: register + login an email, return its bearer token."""
    def _make(email: str, password: str = "Pw12345!") -> str:
        client.post("/api/auth/register", json={"email": email, "password": password})
        resp = client.post("/api/auth/login", data={"username": email, "password": password})
        return resp.json()["access_token"]

    return _make


@pytest.fixture
def auth_client(client, auth_token):
    """A TestClient pre-authenticated as a single default user."""
    token = auth_token("user@example.com")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
