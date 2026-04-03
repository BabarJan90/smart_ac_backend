"""
Agentic AI workstreams:
- Junior Assist: auto-categorises and processes transactions
- Reviewer Assist: identifies anomalies, drafts summaries
- Generative AI: produces letters, reports, and documents

Uses Ollama for local LLM inference (no API key required).
"""
import httpx
import json
from typing import List, Dict, Optional


OLLAMA_BASE_URL = "http://localhost:11434"
# MODEL = "llama3.2"   # Change to any model you have pulled in Ollama
MODEL = "qwen3.5:9b"


async def _ollama_generate(prompt: str, system: str = "") -> str:
    """Call Ollama local LLM."""
    # payload = {
    #     "model": MODEL,
    #     "prompt": prompt,
    #     "system": system,
    #     "stream": False,
    #     "options": {"temperature": 0.3}
    # }
    payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ],
    "stream": False,
    "options": {"temperature": 0.3}
}
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:

            response = await client.post(
                # f"{OLLAMA_BASE_URL}/api/generate",
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            )
            response.raise_for_status()
            # return response.json().get("response", "")
            return response.json().get("message", {}).get("content", "")

    except Exception as e:
        return f"[Ollama unavailable — ensure Ollama is running with `ollama serve`]: {str(e)}"


# ─── Junior Assist Agent ────────────────────────────────────────────────────

async def junior_assist_categorise(transaction: Dict) -> Dict:
    """
    Junior Assist: automatically categorise and enrich a transaction.
    In a real KTP this would process hundreds of transactions autonomously.
    """
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
    raw = await _ollama_generate(prompt, system)
    try:
        result = json.loads(raw)
    except Exception:
        result = {
            "category": transaction.get("category", "Uncategorised"),
            "confidence": 0.5,
            "notes": "Auto-categorised using rule-based fallback."
        }
    result["agent"] = "Junior Assist"
    return result


async def reviewer_assist_analyse(transactions: List[Dict]) -> Dict:
    high_risk = [t for t in transactions if t.get("risk_label") == "high"]
    total = sum(t.get("amount", 0) for t in transactions)

    system = "You are an accounting reviewer. Reply only in JSON."
    
    # Send only a small summary instead of all transactions
    prompt = (
        f"Review summary: {len(transactions)} transactions, "
        f"total £{total:,.2f}, {len(high_risk)} high-risk. "
        f"Top concerns: {[t.get('vendor') for t in high_risk[:3]]}. "
        f"Return JSON with keys: summary, key_concerns (list), "
        f"recommended_actions (list), risk_level (low/medium/high)."
    )
    
    raw = await _ollama_generate(prompt, system)
    try:
        # Clean response in case model adds extra text
        clean = raw.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean)
    except Exception:
        result = {
            "summary": f"Reviewed {len(transactions)} transactions totalling £{total:,.2f}.",
            "key_concerns": [f"{len(high_risk)} high-risk transactions flagged."],
            "recommended_actions": ["Manually verify all high-risk transactions."],
            "risk_level": "high" if len(high_risk) > 3 else "medium"
        }
    result["agent"] = "Reviewer Assist"
    result["stats"] = {
        "total_transactions": len(transactions),
        "total_value": round(total, 2),
        "high_risk_count": len(high_risk),
    }
    return result

# ─── Generative AI Agent ────────────────────────────────────────────────────

async def generate_client_letter(
    client_name: str,
    transactions: List[Dict],
    review_summary: Optional[Dict] = None
) -> str:
    """
    Generative AI: produce a professional client letter based on
    transaction analysis. This is a core KTP deliverable.
    """
    total = sum(t.get("amount", 0) for t in transactions)
    high_risk_count = sum(1 for t in transactions if t.get("risk_label") == "high")
    concerns = review_summary.get("key_concerns", []) if review_summary else []

    system = (
        "You are an AI assistant for a UK accountancy firm. "
        "Write a professional, formal client letter in British English. "
        "Be clear, concise, and constructive. Do not use jargon. "
        "Do not include placeholder text — write the full letter."
    )
    prompt = (
        f"Write a client letter to {client_name} summarising their recent account activity. "
        f"Total transactions: {len(transactions)}, Total value: £{total:,.2f}. "
        f"High-risk items flagged: {high_risk_count}. "
        f"Key concerns identified: {'; '.join(concerns) if concerns else 'None'}. "
        "Include: greeting, summary of activity, any concerns requiring client action, "
        "next steps, and a professional sign-off from 'AccountIQ AI Review Team'."
    )
    letter = await _ollama_generate(prompt, system)
    return letter


async def generate_anomaly_report(anomalous_transactions: List[Dict]) -> str:
    """Generate a formal anomaly detection report for internal review."""
    system = (
        "You are an AI accounting auditor. Write a formal internal anomaly report. "
        "Be precise and use professional accounting language."
    )
    prompt = (
        f"Write an anomaly detection report for {len(anomalous_transactions)} "
        f"flagged transactions: {json.dumps(anomalous_transactions[:10], default=str)}. "
        "Include: executive summary, findings for each anomaly, risk assessment, "
        "and recommended remediation steps."
    )
    return await _ollama_generate(prompt, system)
