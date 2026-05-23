"""
SmartAC — Auth Router
Endpoints for signup, signin, Google OAuth, and token refresh.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.database import get_db
from features.auth import service
from features.auth.schemas import (
    SignupRequest,
    SigninRequest,
    GoogleAuthRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/signin")


# ── Signup ─────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    try:
        return service.signup(db, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Signin ─────────────────────────────────────────────────────────────────

@router.post("/signin", response_model=TokenResponse)
def signin(request: SigninRequest, db: Session = Depends(get_db)):
    """Sign in with email and password."""
    try:
        return service.signin(db, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ── Google OAuth ───────────────────────────────────────────────────────────

@router.post("/google", response_model=TokenResponse)
def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Sign in or register with Google OAuth."""
    try:
        return service.google_auth(db, request.id_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ── Refresh Token ──────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Get new access token using refresh token."""
    try:
        return service.refresh_access_token(db, request.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ── Get Current User ───────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Get current authenticated user."""
    try:
        return service.get_current_user(db, token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))