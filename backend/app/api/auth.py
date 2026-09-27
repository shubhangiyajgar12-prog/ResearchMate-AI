import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, hash_password, verify_password
from app.database.database import get_db
from app.models.user import User
from app.services.email_service import send_welcome_email


router = APIRouter(prefix="/auth", tags=["Authentication"])


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "created_at": user.created_at,
    }


@router.post("/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a ResearchMate account.

    Authentication is intentionally kept independent from ResearchProject.
    The existing ResearchProject model does not contain an owner_id column,
    so signup must not try to modify projects or require that column.
    """
    if "@" not in payload.email or "." not in payload.email.rsplit("@", 1)[-1]:
        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address.",
        )

    name = re.sub(r"\s+", " ", payload.name.strip())
    email = payload.email.strip().lower()

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Please enter your full name.",
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Please sign in.",
        )

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Email is optional. If SMTP is not configured, account creation still
    # succeeds. This keeps registration independent of Gmail setup.
    notification_sent = False
    try:
        notification_sent, _ = send_welcome_email(
            recipient=user.email,
            name=user.name,
        )
    except Exception:
        notification_sent = False

    return {
        "success": True,
        "message": "Account created successfully.",
        "notification_sent": notification_sent,
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": _user_response(user),
    }


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "success": True,
        "message": "Signed in successfully.",
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": _user_response(user),
    }
