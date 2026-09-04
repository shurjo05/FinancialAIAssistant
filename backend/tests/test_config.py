"""Production-config behavior: DB-URL normalization + the prod secret guard."""

import pytest
from pydantic import ValidationError

from app.core.config import _DEV_JWT_SECRET, Settings


@pytest.mark.parametrize(
    "given,expected",
    [
        ("postgresql://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("sqlite:///./finance.db", "sqlite:///./finance.db"),
    ],
)
def test_database_url_normalized_to_psycopg(given, expected):
    s = Settings(database_url=given, jwt_secret="whatever")
    assert s.database_url == expected


def test_production_rejects_dev_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret=_DEV_JWT_SECRET)


def test_production_accepts_real_secret():
    s = Settings(environment="production", jwt_secret="a-strong-random-secret")
    assert s.is_production is True


def test_development_allows_dev_secret():
    s = Settings(environment="development", jwt_secret=_DEV_JWT_SECRET)
    assert s.is_production is False
