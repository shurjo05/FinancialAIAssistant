"""Structured JSON logging.

Configures the root logger to emit one JSON object per line so logs are
machine-parseable in production (Render captures stdout). No third-party
dependency — a small custom formatter over the standard library.

Discipline: never log financial data (amounts, descriptions) or secrets — log
request metadata and derived metrics only. `import logging` below resolves to
the stdlib (absolute imports), not this module.
"""

import json
import logging
import re
import sys

_CONFIGURED = False

# Standard LogRecord attributes, so we can pick out only the structured extras
# a caller passed via logger.info(..., extra={...}).
_RESERVED = set(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}

# Defense-in-depth redaction: we already avoid logging payloads/secrets, but if
# one ever slips into a message or extra, scrub it rather than emit it.
_SECRET_KEYS = {
    "authorization", "token", "access_token", "api_key", "apikey",
    "password", "secret", "jwt_secret",
}
_BEARER_RE = re.compile(r"(Bearer\s+)[\w.\-]+", re.IGNORECASE)


def _scrub(value):
    """Redact Bearer tokens inside any string value."""
    return _BEARER_RE.sub(r"\1[REDACTED]", value) if isinstance(value, str) else value


class JsonFormatter(logging.Formatter):
    """Render each log record as a single-line JSON object (with redaction)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": _scrub(record.getMessage()),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = "[REDACTED]" if key.lower() in _SECRET_KEYS else _scrub(value)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
