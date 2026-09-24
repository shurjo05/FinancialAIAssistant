"""Authentication endpoints: register and login."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.captcha import verify_turnstile
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.email_rules import is_disposable
from app.core.password_policy import password_error
from app.core.ratelimit import client_ip, limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.schemas import PasswordChange, Token, UserCreate, UserOut
from app.services.accounts import seed_sample_accounts

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Shared, sample-data-only account behind "Try the live demo". No one signs in
# with a password — /demo issues a token server-side, so there are no public
# credentials in the wild.
DEMO_EMAIL = "demo@jomoney.app"


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new account (signup-abuse defenses: disposable-email + CAPTCHA)."""
    # Cheap offline check first, then the (possibly networked) CAPTCHA.
    if is_disposable(payload.email):
        raise HTTPException(
            status_code=400,
            detail="Please use a permanent email address — disposable inboxes aren't allowed.",
        )
    if error := password_error(payload.password):
        raise HTTPException(status_code=400, detail=error)
    if not verify_turnstile(payload.turnstile_token, client_ip(request)):
        raise HTTPException(status_code=400, detail="CAPTCHA verification failed. Please try again.")

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


@router.post("/demo", response_model=Token)
@limiter.limit("15/minute")
def demo_login(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Token:
    """Enter the shared demo account (sample data), creating it on first use."""
    import secrets

    from app.api.upload import SAMPLE_CSV, _ingest
    from app.models.models import Transaction

    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        user = User(email=DEMO_EMAIL, hashed_password=hash_password(secrets.token_urlsafe(24)))
        db.add(user)
        db.commit()
        db.refresh(user)

    # Self-healing: load the sample data if the demo account has none yet.
    has_data = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.user_id == user.id)
    )
    if not has_data:
        text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
        _ingest(db, background_tasks, user.id, "sample_transactions.csv", text)

    # Synthetic, clearly labeled balances so the demo shows the accounts feature
    # (the sample CSV itself carries no balances). No-op once seeded.
    seed_sample_accounts(db, user.id)
    db.commit()

    return Token(access_token=create_access_token(str(user.id), user.token_version))


@router.post("/logout-all")
def logout_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Revoke every outstanding token for this user (log out all devices)."""
    if user.email == DEMO_EMAIL:
        # The demo account is shared: revoking its tokens would sign out every
        # visitor currently trying the demo.
        raise HTTPException(status_code=403, detail="The shared demo can't sign out other sessions.")
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
    if error := password_error(payload.new_password):
        raise HTTPException(status_code=400, detail=error)
    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1  # a password change ends every existing session
    db.commit()
    return {"detail": "Password changed. All sessions have been logged out."}
