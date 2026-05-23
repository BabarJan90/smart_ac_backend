"""
SmartAC - Auth Schemas
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


# ── Signup ─────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


# ── Signin ─────────────────────────────────────────────────────────────────

class SigninRequest(BaseModel):
    email: EmailStr
    password: str


# ── Google OAuth ───────────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    id_token: str


# ── Token Response ─────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Refresh Token ──────────────────────────────────────────────────────────

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── User Response ──────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_google: bool

    class Config:
        from_attributes = True