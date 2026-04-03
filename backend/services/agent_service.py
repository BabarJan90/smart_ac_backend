"""
Agentic AI workstreams using Anthropic Claude API.
"""
import httpx
import json
import os
from typing import List, Dict, Optional

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"


async def _claude_generate(prompt: str, system: str = "") -> str:
    if not ANTHROPIC_API_KEY:
        return "[Error: ANTHROPIC_API_KEY not set]"
    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
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


async def junior_assist_categorise(transaction: Dict) -> Dict:
    system = (
        "You are an AI accounting assistant. Categorise the transaction and "
        "return ONLY a JSON object with keys: category (string), "
        "confidence (0.0-1.0), notes (string, max 20 words). No other text."
    )
    prompt = (
        f"Transaction: vendor='{transaction.get('vendor')}', "
        f"amount=£{transaction.get('amount')}, "
        f"description='{transaction.get('description')}'"
    )
    raw = await _claude_generate(prompt, system)
    try:
        clean = raw.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean)
    except Exception:
        result = {"category": transaction.get("category", "Uncategorised"),
                  "confidence": 0.5, "notes": "Rule-based fallback."}
    result["agent"] = "Junior Assist"
    return result


async def reviewer_assist_analyse(transactions: List[Dict]) -> Dict:
    high_risk = [t for t in transactions if t.get("risk_label") == "high"]
    anomalies = [t for t in transactions if t.get("is_anomaly")]
    total = sum(t.get("amount", 0) for t in transactions)
    system = (
        "You are a senior AI accounting reviewer. Be concise and professional. "
        "Return ONLY a JSON object with keys: summary (string), "
        "key_concerns (list of strings), recommended_actions (list of strings), "
        "risk_level (low/medium/high). No other text."
    )
    prompt = (
        f"Review {len(transactions)} transactions. Total: £{total:,.2f}. "
        f"High-risk: {len(high_risk)}. Anomalies: {len(anomalies)}. "
        f"Top vendors: {[t.get('vendor') for t in high_risk[:3]]}. JSON only."
    )
    raw = await _claude_generate(prompt, system)
    try:
        clean = raw.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean)
    except Exception:
        result = {
            "summary": f"Reviewed {len(transactions)} transactions totalling £{total:,.2f}.",
            "key_concerns": [f"{len(high_risk)} high-risk transactions require review."],
            "recommended_actions": ["Manually verify all high-risk flagged transactions."],
            "risk_level": "high" if len(high_risk) > 3 else "medium"
        }
    result["agent"] = "Reviewer Assist"
    result["stats"] = {
        "total_transactions": len(transactions),
        "total_value": round(total, 2),
        "high_risk_count": len(high_risk),
        "anomaly_count": len(anomalies),
    }
    return result


async def generate_client_letter(
    client_name: str,
    transactions: List[Dict],
    review_summary: Optional[Dict] = None
) -> str:
    total = sum(t.get("amount", 0) for t in transactions)
    high_risk_count = sum(1 for t in transactions if t.get("risk_label") == "high")
    concerns = review_summary.get("key_concerns", []) if review_summary else []
    system = (
        "You are an AI assistant for a UK accountancy firm. "
        "Write a professional, formal client letter in British English."
    )
    prompt = (
        f"Write a client letter to {client_name}. "
        f"Transactions: {len(transactions)}, Total: £{total:,.2f}. "
        f"High-risk: {high_risk_count}. Concerns: {'; '.join(concerns) if concerns else 'None'}. "
        "Include greeting, summary, concerns, next steps, sign-off from 'SmartAC AI Review Team'."
    )
    return await _claude_generate(prompt, system)


async def generate_anomaly_report(anomalous_transactions: List[Dict]) -> str:
    system = "You are an AI accounting auditor. Write a formal internal anomaly report."
    prompt = (
        f"Write anomaly report for {len(anomalous_transactions)} flagged transactions: "
        f"{json.dumps(anomalous_transactions[:10], default=str)}. "
        "Include: executive summary, findings, risk assessment, remediation steps."
    )
    return await _claude_generate(prompt, system)