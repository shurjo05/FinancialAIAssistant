"""Cloudflare Turnstile verification — a bot gate on registration.

Server-side check that the CAPTCHA token the browser submitted is valid. When
`TURNSTILE_SECRET` is unset the check is skipped (returns True), so local dev and
tests run unchanged — the same feature-flag pattern as the Gemini/Plaid keys.
"""

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.captcha")

_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_enabled() -> bool:
    return bool(settings.turnstile_secret)


def verify_turnstile(token: str | None, remote_ip: str | None = None) -> bool:
    """Verify a Turnstile token with Cloudflare. Returns True when disabled.

    Never raises: a network/API failure is treated as a failed verification
    (fail-closed) so an outage can't be used to bypass the gate.
    """
    if not turnstile_enabled():
        return True
    if not token:
        return False

    data = {"secret": settings.turnstile_secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        resp = httpx.post(_VERIFY_URL, data=data, timeout=5.0)
        return bool(resp.json().get("success") is True)
    except Exception:
        logger.warning("turnstile verification failed to reach Cloudflare; rejecting")
        return False
