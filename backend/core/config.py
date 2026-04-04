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

# ── Database ───────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./accountiq.db")

# ── App ────────────────────────────────────────────────────────────────────
APP_TITLE: str = "SmartAC"
APP_DESCRIPTION: str = "AI-Powered Accounting Platform — KTP Demo"
APP_VERSION: str = "1.0.0"
