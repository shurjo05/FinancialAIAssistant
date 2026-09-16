"""Auth dependency: resolve the current user from the Bearer token."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User

# tokenUrl is where the interactive docs send credentials to get a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT, load the user, verify the token version, or raise 401."""
    claims = decode_token(token)
    if claims is None or claims["sub"] is None:
        raise _credentials_error
    try:
        user = db.get(User, int(claims["sub"]))
    except (TypeError, ValueError):
        raise _credentials_error from None
    if user is None:
        raise _credentials_error
    # Revocation check: a token issued before the user's version was bumped
    # (logout-all / password change) is now invalid.
    if claims["ver"] != user.token_version:
        raise _credentials_error
    # Expose the user id for the per-user rate limiter's key function.
    request.state.user_id = user.id
    return user
