"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.schemas import PasswordChange, Token, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new account."""
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Verify credentials and return a JWT. `username` field carries the email."""
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id), user.token_version))


@router.post("/logout-all")
def logout_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Revoke every outstanding token for this user (log out all devices)."""
    user.token_version += 1
    db.commit()
    return {"detail": "All sessions have been logged out."}


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Change the password and revoke all existing sessions."""
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1  # a password change ends every existing session
    db.commit()
    return {"detail": "Password changed. All sessions have been logged out."}
