"""
Transaction service — fuzzy logic risk scoring + NLP categorisation.
Pure business logic, no HTTP, no DB queries.
"""
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Dict, Tuple

# ── Fuzzy Logic Setup ──────────────────────────────────────────────────────

def _build_fuzzy_system():
    """Build the fuzzy control system once at module load."""
    amount        = ctrl.Antecedent(np.arange(0, 10001, 1), "amount")
    vendor_trust  = ctrl.Antecedent(np.arange(0, 1.01, 0.01), "vendor_trust")
    frequency     = ctrl.Antecedent(np.arange(0, 1.01, 0.01), "frequency")
    risk          = ctrl.Consequent(np.arange(0, 101, 1), "risk")

    # Membership functions — amount
    amount["low"]    = fuzz.trimf(amount.universe, [0, 0, 1000])
    amount["medium"] = fuzz.trimf(amount.universe, [500, 2500, 5000])
    amount["high"]   = fuzz.trimf(amount.universe, [3000, 10000, 10000])

    # Membership functions — vendor trust (0 = untrusted, 1 = trusted)
    vendor_trust["low"]    = fuzz.trimf(vendor_trust.universe, [0, 0, 0.4])
    vendor_trust["medium"] = fuzz.trimf(vendor_trust.universe, [0.3, 0.5, 0.7])
    vendor_trust["high"]   = fuzz.trimf(vendor_trust.universe, [0.6, 1, 1])

    # Membership functions — frequency (0 = rare, 1 = frequent)
    frequency["rare"]     = fuzz.trimf(frequency.universe, [0, 0, 0.4])
    frequency["moderate"] = fuzz.trimf(frequency.universe, [0.3, 0.5, 0.7])
    frequency["frequent"] = fuzz.trimf(frequency.universe, [0.6, 1, 1])

    # Membership functions — risk output
    risk["low"]    = fuzz.trimf(risk.universe, [0, 0, 40])
    risk["medium"] = fuzz.trimf(risk.universe, [30, 50, 70])
    risk["high"]   = fuzz.trimf(risk.universe, [60, 100, 100])

    # Fuzzy rules
    rules = [
        ctrl.Rule(amount["high"] & vendor_trust["low"],    risk["high"]),
        ctrl.Rule(amount["high"] & frequency["rare"],      risk["high"]),
        ctrl.Rule(vendor_trust["low"] & frequency["rare"], risk["high"]),
        ctrl.Rule(amount["medium"] & vendor_trust["low"],  risk["medium"]),
        ctrl.Rule(amount["high"] & vendor_trust["medium"], risk["medium"]),
        ctrl.Rule(amount["medium"] & frequency["rare"],    risk["medium"]),
        ctrl.Rule(amount["low"] & vendor_trust["high"],    risk["low"]),
        ctrl.Rule(amount["low"] & frequency["frequent"],   risk["low"]),
        ctrl.Rule(vendor_trust["high"] & frequency["frequent"], risk["low"]),
    ]

    system = ctrl.ControlSystem(rules)
    return ctrl.ControlSystemSimulation(system)


_fuzzy_sim = _build_fuzzy_system()


# ── Risk Scoring ───────────────────────────────────────────────────────────

def calculate_risk(
    amount: float,
    vendor_trust: float = 0.5,
    frequency: float = 0.5,
) -> Tuple[float, str, str]:
    """
    Run fuzzy logic risk scoring.
    Returns: (risk_score 0-100, risk_label, xai_explanation)
    """
    try:
        _fuzzy_sim.input["amount"]       = min(max(amount, 0), 10000)
        _fuzzy_sim.input["vendor_trust"] = min(max(vendor_trust, 0), 1)
        _fuzzy_sim.input["frequency"]    = min(max(frequency, 0), 1)
        _fuzzy_sim.compute()
        score = round(_fuzzy_sim.output["risk"], 1)
    except Exception:
        # Fallback rule-based scoring
        score = 80.0 if amount > 5000 else 50.0 if amount > 1000 else 20.0

    # Label
    label = "high" if score >= 65 else "medium" if score >= 35 else "low"

    # XAI — plain English explanation
    explanation = _build_xai_explanation(score, label, amount, vendor_trust, frequency)

    return score, label, explanation


def _build_xai_explanation(
    score: float,
    label: str,
    amount: float,
    vendor_trust: float,
    frequency: float,
) -> str:
    reasons = []
    if amount > 5000:
        reasons.append(f"the transaction amount of £{amount:,.2f} is unusually high")
    elif amount > 1500:
        reasons.append(f"the transaction amount of £{amount:,.2f} is moderately elevated")

    if vendor_trust < 0.3:
        reasons.append("this vendor is unrecognised or untrusted")
    elif vendor_trust < 0.5:
        reasons.append("this vendor has a low trust rating")

    if frequency < 0.3:
        reasons.append("this vendor appears infrequently in the accounts")

    if not reasons:
        reasons.append("all indicators are within normal ranges")

    reason_text = ", ".join(reasons)
    return (
        f"Risk assessed as {label.upper()} (score: {score}/100). "
        f"Contributing factors: {reason_text}."
    )


# ── NLP Categorisation ─────────────────────────────────────────────────────

CATEGORY_KEYWORDS: Dict[str, list] = {
    "Software & Subscriptions": ["software", "saas", "subscription", "licence", "license", "cloud", "api", "github", "aws", "azure"],
    "Office Supplies":          ["office", "stationery", "supplies", "paper", "printer", "desk"],
    "Travel & Transport":       ["travel", "flight", "hotel", "taxi", "uber", "train", "fuel", "mileage"],
    "Marketing & Advertising":  ["marketing", "advertising", "ads", "campaign", "social media", "seo", "google ads"],
    "Professional Services":    ["consulting", "legal", "accountant", "solicitor", "audit", "advisory"],
    "Utilities":                ["electricity", "gas", "water", "broadband", "internet", "telephone", "phone"],
    "Payroll":                  ["salary", "wage", "payroll", "pension", "bonus", "staff"],
    "Equipment":                ["equipment", "hardware", "laptop", "computer", "machine", "device"],
    "Food & Entertainment":     ["food", "lunch", "dinner", "restaurant", "coffee", "entertainment", "client meal"],
}


def categorise_transaction(vendor: str, description: str = "") -> str:
    """Simple keyword-based NLP categorisation."""
    text = f"{vendor} {description}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "General Expenses"


def assess_vendor_trust(vendor: str) -> float:
    """
    Simple heuristic vendor trust score (0-1).
    In production this would query a vendor database.
    """
    vendor_lower = vendor.lower()
    known_trusted = ["amazon", "microsoft", "google", "apple", "hmrc", "bbc", "bt", "virgin", "vodafone"]
    known_unknown = ["unknown", "misc", "cash", "unverified", "other"]

    if any(t in vendor_lower for t in known_trusted):
        return 0.9
    if any(u in vendor_lower for u in known_unknown):
        return 0.1
    if len(vendor) < 5:
        return 0.2
    return 0.5
