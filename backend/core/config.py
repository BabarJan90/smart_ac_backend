"""
Central configuration — reads from environment variables / .env file.
All settings live here, nowhere else.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Anthropic ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
ANTHROPIC_MAX_TOKENS: int = 1024
ANTHROPIC_MAX_TOKENS_AGENT: int = 4096

# ── Database ───────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./accountiq.db")

# ── App ────────────────────────────────────────────────────────────────────
APP_TITLE: str = "SmartAC"
APP_DESCRIPTION: str = "AI-Powered Accounting Platform"
APP_VERSION: str = "1.0.0"

# ── Email ──────────────────────────────────────────────────────────────────
GMAIL_ADDRESS: str      = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
ALERT_EMAIL: str        = os.getenv("ALERT_EMAIL", "")

# ── Product API ────────────────────────────────────────────────────────────
PRODUCT_API_URL: str = "https://dummyjson.com/products?limit=100"
CACHE_TTL_SECONDS = 1800  # 30 minutes

# ── Auth ───────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")