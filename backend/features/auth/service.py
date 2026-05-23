"""
SmartAC — Auth Service
Handles signup, signin, Google OAuth, and JWT tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests

from core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    GOOGLE_CLIENT_ID,
)
from features.auth.models import User
from features.auth.schemas import SignupRequest, SigninRequest

# ── Password hashing ───────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Tokens ─────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


# ── User queries ───────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


# ── Signup ─────────────────────────────────────────────────────────────────

def signup(db: Session, request: SignupRequest) -> dict:
    # Check if email already exists
    existing = get_user_by_email(db, request.email)
    if existing:
        raise ValueError("Email already registered")

    # Create user
    user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=hash_password(request.password),
        is_google=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Return tokens
    return {
        "access_token": create_access_token(user.id, user.email),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


# ── Signin ─────────────────────────────────────────────────────────────────

def signin(db: Session, request: SigninRequest) -> dict:
    user = get_user_by_email(db, request.email)
    if not user:
        raise ValueError("Invalid email or password")
    if user.is_google:
        raise ValueError("Please sign in with Google")
    if not verify_password(request.password, user.hashed_password):
        raise ValueError("Invalid email or password")
    if not user.is_active:
        raise ValueError("Account is deactivated")

    return {
        "access_token": create_access_token(user.id, user.email),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


# ── Google OAuth ───────────────────────────────────────────────────────────

def google_auth(db: Session, id_token_str: str) -> dict:
    try:
        # Verify Google token
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise ValueError("Invalid Google token")

    email = idinfo.get("email")
    full_name = idinfo.get("name")
    google_id = idinfo.get("sub")

    # Check if user exists
    user = get_user_by_email(db, email)

    if not user:
        # Create new user
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            is_google=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "access_token": create_access_token(user.id, user.email),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


# ── Refresh Token ──────────────────────────────────────────────────────────

def refresh_access_token(db: Session, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        user_id = int(payload.get("sub"))
    except JWTError:
        raise ValueError("Invalid or expired refresh token")

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise ValueError("User not found")

    return {
        "access_token": create_access_token(user.id, user.email),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


# ── Get current user from token ────────────────────────────────────────────

def get_current_user(db: Session, token: str) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        user_id = int(payload.get("sub"))
    except JWTError:
        raise ValueError("Invalid or expired token")

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise ValueError("User not found")
    return user