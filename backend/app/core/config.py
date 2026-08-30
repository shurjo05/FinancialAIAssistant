"""
Application configuration.

Loads settings from environment variables (and a local .env file) using
pydantic-settings. Import the singleton `settings` anywhere you need config,
e.g. `from app.core.config import settings`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Where the SQLite database file lives (relative to the backend/ folder).
    database_url: str = "sqlite:///./finance.db"

    # CORS: the origin the React dev server runs on.
    frontend_origin: str = "http://localhost:5173"

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


# Single shared instance imported across the app.
settings = Settings()
