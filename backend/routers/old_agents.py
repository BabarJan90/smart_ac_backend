"""Agents router — Junior Assist, Reviewer Assist, Generative AI."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from db.database import get_db, Transaction, GeneratedDocument, AuditLog
from backend.services.agent_service_with_ollama import (
    junior_assist_categorise,
    reviewer_assist_analyse,
    generate_client_letter,
    generate_anomaly_report,
)
import json

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/junior-assist/{transaction_id}")
async def run_junior_assist(transaction_id: int, db: Session = Depends(get_db)):
    """Junior Assist: enrich and auto-categorise a single transaction."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    result = await junior_assist_categorise({
        "vendor": tx.vendor,
        "amount": tx.amount,
        "description": tx.description,
        "category": tx.category,
    })

    tx.category = result.get("category", tx.category)
    db.commit()

    log = AuditLog(
        action="junior_assist_categorise",
        transaction_id=tx.id,
        input_data=json.dumps({"vendor": tx.vendor, "amount": tx.amount}),
        output_data=json.dumps(result),
        model_used="Ollama/llama3.2",
        justification=result.get("notes", ""),
    )
    db.add(log)
    db.commit()

    return result


@router.post("/reviewer-assist")
async def run_reviewer_assist(
    # limit: int = 50,
    limit: int = 10,

    risk_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Reviewer Assist: batch analysis and anomaly detection."""
    query = db.query(Transaction)
    if risk_filter:
        query = query.filter(Transaction.risk_label == risk_filter)
    transactions = query.limit(limit).all()

    tx_list = [
        {
            "id": t.id, "vendor": t.vendor, "amount": t.amount,
            "category": t.category, "risk_label": t.risk_label,
            "risk_score": t.risk_score, "is_anomaly": t.is_anomaly,
            "explanation": t.explanation,
        }
        for t in transactions
    ]

    result = await reviewer_assist_analyse(tx_list)

    log = AuditLog( 
        action="reviewer_assist_batch",
        input_data=json.dumps({"transaction_count": len(tx_list)}),
        output_data=json.dumps(result),
        model_used="Ollama/llama3.2",
        justification=result.get("summary", ""),
    )
    db.add(log)
    db.commit()

    return result


class LetterRequest(BaseModel):
    client_name: str
    transaction_limit: int = 50


@router.post("/generate-letter")
async def run_generate_letter(request: LetterRequest, db: Session = Depends(get_db)):
    """Generative AI: produce a professional client letter."""
    transactions = db.query(Transaction).limit(request.transaction_limit).all()
    tx_list = [
        {"vendor": t.vendor, "amount": t.amount,
         "risk_label": t.risk_label, "category": t.category}
        for t in transactions
    ]

    review = await reviewer_assist_analyse(tx_list)
    letter = await generate_client_letter(request.client_name, tx_list, review)

    doc = GeneratedDocument(
        doc_type="client_letter",
        content=letter,
        transaction_ids=",".join(str(t.id) for t in transactions),
    )
    db.add(doc)

    log = AuditLog(
        action="generate_client_letter",
        input_data=json.dumps({"client": request.client_name, "tx_count": len(tx_list)}),
        output_data=letter[:500],
        model_used="Ollama/llama3.2",
        justification="Generative AI client letter based on transaction analysis.",
    )
    db.add(log)
    db.commit()
    db.refresh(doc)

    return {"document_id": doc.id, "letter": letter}


@router.post("/generate-anomaly-report")
async def run_anomaly_report(db: Session = Depends(get_db)):
    """Generate a formal anomaly detection report."""
    anomalies = db.query(Transaction).filter(Transaction.is_anomaly == True).all()
    if not anomalies:
        return {"message": "No anomalies found.", "report": None}

    tx_list = [
        {"id": t.id, "vendor": t.vendor, "amount": t.amount,
         "risk_score": t.risk_score, "explanation": t.explanation}
        for t in anomalies
    ]
    report = await generate_anomaly_report(tx_list)

    doc = GeneratedDocument(
        doc_type="anomaly_report",
        content=report,
        transaction_ids=",".join(str(t.id) for t in anomalies),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"document_id": doc.id, "report": report}


@router.get("/audit-log")
def get_audit_log(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """GDPR audit trail — every AI decision logged."""
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": l.id,
            "timestamp": str(l.timestamp),
            "action": l.action,
            "transaction_id": l.transaction_id,
            "model_used": l.model_used,
            "justification": l.justification,
        }
        for l in logs
    ]
