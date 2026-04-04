"""
Agent service — Junior Assist and Reviewer Assist AI workstreams.
Uses Claude API via core.claude module.
"""
import json
from typing import Dict, List, Optional
from core.claude import claude_generate


# ── Junior Assist ──────────────────────────────────────────────────────────

async def junior_assist(transaction: Dict) -> Dict:
    """
    Categorise a single transaction using Claude AI.
    Returns category, confidence, and notes.
    """
    system = (
        "You are an AI accounting assistant. Categorise the transaction and "
        "return ONLY a JSON object with keys: category (string), "
        "confidence (0.0-1.0), notes (string, max 20 words). No other text."
    )
    prompt = (
        f"Transaction: vendor='{transaction.get('vendor')}', "
        f"amount=£{transaction.get('amount')}, "
        f"description='{transaction.get('description', '')}'"
    )
    raw = await claude_generate(prompt, system)

    try:
        clean = raw.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean)
    except Exception:
        result = {
            "category": transaction.get("category", "General Expenses"),
            "confidence": 0.5,
            "notes": "Rule-based fallback categorisation applied."
        }

    result["agent"] = "Junior Assist"
    result["transaction_id"] = transaction.get("id")
    return result


# ── Reviewer Assist ────────────────────────────────────────────────────────

async def reviewer_assist(transactions: List[Dict]) -> Dict:
    """
    Analyse a batch of transactions and produce a review summary.
    """
    high_risk  = [t for t in transactions if t.get("risk_label") == "high"]
    anomalies  = [t for t in transactions if t.get("is_anomaly")]
    total      = sum(t.get("amount", 0) for t in transactions)

    system = (
        "You are a senior AI accounting reviewer. Be concise and professional. "
        "Return ONLY a JSON object with keys: summary (string), "
        "key_concerns (list of strings), recommended_actions (list of strings), "
        "risk_level (low/medium/high). No other text."
    )
    prompt = (
        f"Review {len(transactions)} transactions. Total: £{total:,.2f}. "
        f"High-risk: {len(high_risk)}. Anomalies: {len(anomalies)}. "
        f"Top high-risk vendors: {[t.get('vendor') for t in high_risk[:3]]}. "
        f"Return JSON only."
    )
    raw = await claude_generate(prompt, system)

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
            "key_concerns": [f"{len(high_risk)} high-risk transactions require manual review."],
            "recommended_actions": ["Verify all high-risk flagged transactions with the client."],
            "risk_level": "high" if len(high_risk) > 3 else "medium",
        }

    result["agent"] = "Reviewer Assist"
    result["stats"] = {
        "total_transactions": len(transactions),
        "total_value": round(total, 2),
        "high_risk_count": len(high_risk),
        "anomaly_count": len(anomalies),
    }
    return result


# ── Generative AI ──────────────────────────────────────────────────────────

async def generate_client_letter(
    client_name: str,
    transactions: List[Dict],
    review_summary: Optional[Dict] = None,
) -> str:
    total            = sum(t.get("amount", 0) for t in transactions)
    high_risk_count  = sum(1 for t in transactions if t.get("risk_label") == "high")
    concerns         = review_summary.get("key_concerns", []) if review_summary else []

    system = (
        "You are an AI assistant for a UK accountancy firm. "
        "Write a professional, formal client letter in British English. "
        "Be clear, concise, and constructive."
    )
    prompt = (
        f"Write a client letter to {client_name} summarising their account activity. "
        f"Total transactions: {len(transactions)}, Total value: £{total:,.2f}. "
        f"High-risk items flagged: {high_risk_count}. "
        f"Key concerns: {'; '.join(concerns) if concerns else 'None identified'}. "
        "Include: greeting, account summary, any concerns, recommended next steps, "
        "and sign-off from 'SmartAC AI Review Team'."
    )
    return await claude_generate(prompt, system)


async def generate_anomaly_report(anomalous_transactions: List[Dict]) -> str:
    system = (
        "You are an AI accounting auditor. "
        "Write a formal internal anomaly report in professional accounting language."
    )
    prompt = (
        f"Write an anomaly detection report for {len(anomalous_transactions)} "
        f"flagged transactions: {json.dumps(anomalous_transactions[:10], default=str)}. "
        "Include: executive summary, detailed findings, risk assessment, "
        "and recommended remediation steps."
    )
    return await claude_generate(prompt, system)
