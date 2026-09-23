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
    # Cheaper/lighter models to fall through to when the primary hits its free-tier
    # quota (429/RESOURCE_EXHAUSTED). Free quotas are PER MODEL, so a chain roughly
    # sums the headroom on one key; `-lite` variants tend to have the most generous
    # free tiers. Comma-separated; set to "" to disable fallback. NOTE: a model must
    # be callable by THIS project — some listed models (e.g. gemini-2.5-flash) are
    # "no longer available to new users" and 404, which is NOT a quota error; these
    # were verified callable on a new-tier key.
    google_fallback_models: str = "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-flash-lite-latest"
    openai_api_key: str = ""

    # Hard ceiling on Gemini calls per (UTC) day across the whole instance. Past
    # this, Jo transparently serves the deterministic fallback instead of calling
    # the API — a budget backstop that no per-minute rate limit can guarantee.
    gemini_daily_cap: int = 300

    # --- Signup abuse prevention ---
    # Cloudflare Turnstile secret key (server-side). Blank → CAPTCHA verification
    # is skipped, so local dev/tests are unchanged. Pair it with the public site
    # key on the frontend (VITE_TURNSTILE_SITE_KEY); set both or neither.
    turnstile_secret: str = ""

    # --- Bank sync: Plaid (optional; sandbox) ---
    # Blank client id/secret → the "connect a bank" feature is disabled (endpoints
    # 503, button hidden), app otherwise unchanged. Sandbox uses fake institutions
    # and the test login user_good / pass_good — never real bank credentials.
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"
    # Fernet key for encrypting Plaid access tokens at rest (generate with
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
    # Blank → dev/test only, an ephemeral per-process key is used; PRODUCTION MUST
    # set this or a restart can't decrypt previously stored tokens.
    plaid_encryption_key: str = ""

    @property
    def plaid_configured(self) -> bool:
        return bool(self.plaid_client_id and self.plaid_secret)

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

    @property
    def model_chain(self) -> list[str]:
        """Primary model first, then fallbacks — deduped, order preserved.

        Gemini tries each in turn, dropping to the next only on a quota error, so
        the effective free-tier headroom is roughly the sum across models.
        """
        chain = [self.google_model]
        chain += [m.strip() for m in self.google_fallback_models.split(",") if m.strip()]
        return list(dict.fromkeys(chain))  # dedupe, keep order


# Single shared instance imported across the app.
settings = Settings()
