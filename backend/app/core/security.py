"""Password hashing and JWT creation/verification."""

import datetime

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt only considers the first 72 bytes of a password; truncate explicitly so
# longer inputs hash/verify consistently instead of raising.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX_BYTES], hashed.encode("utf-8"))


def create_access_token(subject: str, token_version: int = 0) -> str:
    """Create a signed JWT: `sub` is the user id, `ver` the token version."""
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "ver": token_version, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    """Return the token's claims ({sub, ver}) if valid, else None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"sub": payload.get("sub"), "ver": payload.get("ver", 0)}
    except JWTError:
        return None
