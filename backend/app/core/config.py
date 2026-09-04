"""
Application configuration.

Loads settings from environment variables (and a local .env file) using
pydantic-settings. Import the singleton `settings` anywhere you need config,
e.g. `from app.core.config import settings`.
"""

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "dev-insecure-change-me"


class Settings(BaseSettings):
    # "development" locally/in tests; set ENVIRONMENT=production when deployed.
    environment: str = "development"

    # Where the SQLite database file lives (relative to the backend/ folder).
    database_url: str = "sqlite:///./finance.db"

    # CORS: the origin the React dev server runs on.
    frontend_origin: str = "http://localhost:5173"

    # --- Auth (JWT) ---
    # Dev default only; production MUST override JWT_SECRET via the environment.
    jwt_secret: str = _DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # --- AI providers (all optional; blank = disabled) ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    google_api_key: str = ""
    google_model: str = "gemini-3.6-flash"
    openai_api_key: str = ""

    # Tells pydantic to read a .env file and ignore unknown keys.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Rewrite managed-Postgres URLs to the psycopg-v3 driver.

        Neon/Render hand out `postgresql://` (and some providers `postgres://`),
        but our driver needs the explicit `postgresql+psycopg://` prefix. This
        lets the provider's connection string be pasted in verbatim.
        """
        for scheme in ("postgresql://", "postgres://"):
            if v.startswith(scheme):
                return "postgresql+psycopg://" + v[len(scheme):]
        return v

    @model_validator(mode="after")
    def _require_prod_secret(self) -> "Settings":
        """Never run production on the insecure dev JWT secret."""
        if self.is_production and self.jwt_secret == _DEV_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set to a strong secret in production "
                "(it is still the insecure dev default)."
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


# Single shared instance imported across the app.
settings = Settings()
