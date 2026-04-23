from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.email import send_high_risk_alert, send_report_ready
from features.transactions import repository as tx_repo
from features.agents import service as agent_service
from features.agents.schemas import (
    ReviewerAssistRequest, ReviewerAssistResponse, ReviewerStatsDto,
    JuniorAssistResponse, CategorizationDto,
    GenerateLetterRequest, ClientLetterResponse,
    AnomalyReportResponse,
)
from features.documents import repository as doc_repo
from features.audit import repository as audit_repo
from core.claude import claude_generate
from typing import List, Optional

from pydantic import BaseModel

class SpeechRecommendationRequest(BaseModel):
    text: str
    client_name: Optional[str] = None


class SpeechRecommendationResponse(BaseModel):
    recommendation: str
    services: List[str]
    next_steps: List[str]

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/junior-assist", response_model=JuniorAssistResponse)
async def junior_assist_all(db: Session = Depends(get_db)):
    """Run Junior Assist on all unprocessed transactions — returns list shape Flutter expects."""
    unprocessed = tx_repo.get_unprocessed(db)
    categorisations = []

    for t in unprocessed[:20]:
        result = await agent_service.junior_assist(t.__dict__)
        tx_repo.update_category(db, t.id, result.get("category", t.category))
        categorisations.append(CategorizationDto(
            transaction_id=t.id,
            vendor=t.vendor,
            category=result.get("category"),
            confidence=result.get("confidence"),
            notes=result.get("notes"),
        ))
        audit_repo.log(db, action="junior_assist", entity_id=t.id,
                       details=f"Category: {result.get('category')}, Confidence: {result.get('confidence')}")

    return JuniorAssistResponse(
        status="success",
        processed=len(categorisations),
        categorisations=categorisations,
    )


@router.post("/junior-assist/{transaction_id}", response_model=JuniorAssistResponse)
async def junior_assist_single(transaction_id: int, db: Session = Depends(get_db)):
    """Run Junior Assist on a single transaction — still returns list shape."""
    t = tx_repo.get_by_id(db, transaction_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")

    result = await agent_service.junior_assist(t.__dict__)
    tx_repo.update_category(db, transaction_id, result.get("category", t.category))

    audit_repo.log(db, action="junior_assist", entity_id=transaction_id,
                   details=f"Category: {result.get('category')}, Confidence: {result.get('confidence')}")

    return JuniorAssistResponse(
        status="success",
        processed=1,
        categorisations=[CategorizationDto(
            transaction_id=t.id,
            vendor=t.vendor,
            category=result.get("category"),
            confidence=result.get("confidence"),
            notes=result.get("notes"),
        )],
    )


@router.post("/reviewer-assist", response_model=ReviewerAssistResponse)
async def reviewer_assist(
    request: ReviewerAssistRequest,
    db: Session = Depends(get_db),
):
    transactions = tx_repo.get_all(db, limit=request.limit, risk_filter=request.risk_filter)
    tx_dicts = [t.__dict__ for t in transactions]
    result = await agent_service.reviewer_assist(tx_dicts)

    audit_repo.log(db, action="reviewer_assist",
                   details=f"Reviewed {len(transactions)} transactions. Risk: {result.get('risk_level')}")

    raw_stats = result.get("stats", {})
    return ReviewerAssistResponse(
        agent=result.get("agent", "Reviewer Assist"),
        summary=result.get("summary", ""),
        key_concerns=result.get("key_concerns", []),
        recommended_actions=result.get("recommended_actions", []),
        risk_level=result.get("risk_level", "low"),
        stats=ReviewerStatsDto(
            total_transactions=raw_stats.get("total_transactions", 0),
            total_value=raw_stats.get("total_value", 0.0),
            high_risk_count=raw_stats.get("high_risk_count", 0),
            anomaly_count=raw_stats.get("anomaly_count", 0),
        ),
    )


@router.post("/generate-letter", response_model=ClientLetterResponse)
async def generate_letter(request: GenerateLetterRequest, db: Session = Depends(get_db)):
    transactions = tx_repo.get_all(db, limit=request.transaction_limit)
    tx_dicts = [t.__dict__ for t in transactions]
    letter = await agent_service.generate_client_letter(request.client_name, tx_dicts)

    doc_repo.create(db, title=f"Client Letter — {request.client_name}",
                    content=letter, doc_type="client_letter")
    audit_repo.log(db, action="generate_letter",
                   details=f"Generated letter for {request.client_name}")

    return ClientLetterResponse(
        status="success",
        client=request.client_name,
        letter=letter,
    )


@router.post("/generate-anomaly-report", response_model=AnomalyReportResponse)
async def generate_anomaly_report(db: Session = Depends(get_db)):
    anomalies = tx_repo.get_anomalies(db)
    anomaly_dicts = [t.__dict__ for t in anomalies]
    report = await agent_service.generate_anomaly_report(anomaly_dicts)

    doc_repo.create(db, title="Anomaly Detection Report",
                    content=report, doc_type="anomaly_report")
    audit_repo.log(db, action="generate_anomaly_report",
                   details=f"Report generated for {len(anomalies)} anomalies")
    
    # Send high risk alert email with report
    if anomalies:
        send_high_risk_alert(
            high_risk_transactions=anomaly_dicts,
            anomaly_count=len(anomalies),
            report_content=report,
        )

    return AnomalyReportResponse(
        status="success",
        report=report,
    )

@router.post("/speech-recommendation",
             response_model=SpeechRecommendationResponse)
async def speech_recommendation(
    request: SpeechRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Takes transcribed speech and returns SmartAC service recommendations."""

    stats = tx_repo.get_stats(db)

    system = """
    You are a SmartAC sales and advisory AI assistant for a UK accounting firm.
    SmartAC offers these services:
    1. Transaction Risk Analysis — fuzzy logic risk scoring
    2. AI Categorisation — automatic transaction categorisation
    3. Anomaly Detection — identify suspicious transactions
    4. Client Letters — AI generated professional letters
    5. Audit Trail — GDPR compliant decision logging
    6. Orchestrator — fully autonomous accounting AI agent

    Based on what the customer says, recommend the most relevant services.
    Return ONLY a JSON object with keys:
    - recommendation (string: 2-3 sentences)
    - services (list of relevant service names)
    - next_steps (list of 2-3 action items)
    No other text.
    """

    prompt = (
        f"Customer said: '{request.text}'\n"
        f"Their account has {stats.total_transactions} transactions, "
        f"{stats.risk_distribution.high} high risk items, "
        f"{stats.anomaly_count} anomalies.\n"
        f"What SmartAC services would you recommend?"
    )

    import json
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
            "recommendation": "Based on your account activity, SmartAC can help you manage risk and automate your accounting processes.",
            "services": ["Transaction Risk Analysis", "Anomaly Detection"],
            "next_steps": ["Run the Orchestrator", "Review high risk transactions"],
        }

    audit_repo.log(db, action="speech_recommendation",
                   details=f"Query: {request.text[:100]}")

    return SpeechRecommendationResponse(**result)


@router.post("/speech-recommendation",
             response_model=SpeechRecommendationResponse)
async def speech_recommendation(
    request: SpeechRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Takes transcribed speech and returns SmartAC service recommendations."""

    stats = tx_repo.get_stats(db)

    system = """
    You are a SmartAC sales and advisory AI assistant for a UK accounting firm.
    SmartAC offers these services:
    1. Transaction Risk Analysis - fuzzy logic risk scoring
    2. AI Categorisation - automatic transaction categorisation
    3. Anomaly Detection - identify suspicious transactions
    4. Client Letters - AI generated professional letters
    5. Audit Trail - GDPR compliant decision logging
    6. Orchestrator - fully autonomous accounting AI agent

    Based on what the customer says, recommend the most relevant services.
    Return ONLY a JSON object with keys:
    - recommendation (string: 2-3 sentences)
    - services (list of relevant service names)
    - next_steps (list of 2-3 action items)
    No other text.
    """

    prompt = (
        f"Customer said: '{request.text}'\n"
        f"Their account has {stats.total_transactions} transactions, "
        f"{stats.risk_distribution.high} high risk items, "
        f"{stats.anomaly_count} anomalies.\n"
        f"What SmartAC services would you recommend?"
    )

    import json
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
            "recommendation": "Based on your account activity, SmartAC can help you manage risk and automate your accounting processes.",
            "services": ["Transaction Risk Analysis", "Anomaly Detection"],
            "next_steps": ["Run the Orchestrator", "Review high risk transactions"],
        }

    audit_repo.log(db, action="speech_recommendation",
                   details=f"Query: {request.text[:100]}")

    return SpeechRecommendationResponse(**result)