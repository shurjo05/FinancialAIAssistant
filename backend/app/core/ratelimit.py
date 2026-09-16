"""Request rate limiting (slowapi).

Two keying strategies:
  - `client_ip`  : real client IP, honoring Render's proxy — for pre-auth
                   endpoints (login/register), i.e. brute-force / enumeration.
  - `user_or_ip` : the authenticated user id when available (set by
                   get_current_user), else the IP — for the expensive /query
                   path, so one account can't exhaust the LLM budget.

In-memory storage is fine for the single Render instance (a distributed limiter
would need Redis, which we deliberately avoid at this scale).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


def client_ip(request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()  # first hop = the real client
    return get_remote_address(request)


def user_or_ip(request) -> str:
    uid = getattr(request.state, "user_id", None)
    return f"user:{uid}" if uid is not None else client_ip(request)


limiter = Limiter(key_func=client_ip)
