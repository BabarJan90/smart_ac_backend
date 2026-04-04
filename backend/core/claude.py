"""
Claude API client — single place for all AI calls.
Every feature imports _claude_generate from here.
"""
import httpx
from core.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


async def claude_generate(prompt: str, system: str = "") -> str:
    """Call Claude API and return the text response."""
    if not ANTHROPIC_API_KEY:
        return "[Error: ANTHROPIC_API_KEY not set in environment]"

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": ANTHROPIC_MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
    except Exception as e:
        return f"[Claude API error]: {str(e)}"
