"""Auth dependency: resolve the current user from the Bearer token."""

from fastapi import Depends, HTTPException, status
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
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT, load the user, or raise 401."""
    subject = decode_token(token)
    if subject is None:
        raise _credentials_error
    user = db.get(User, int(subject))
    if user is None:
        raise _credentials_error
    return user
