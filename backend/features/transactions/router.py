from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from core.database import get_db
from features.transactions import repository, service
from features.transactions.schemas import TransactionCreate, TransactionResponse, AccountStats

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=List[TransactionResponse])
def get_transactions(
    limit: int = 100,
    risk_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    transactions = repository.get_all(db, limit=limit, risk_filter=risk_filter)
    return [TransactionResponse.from_orm_model(t) for t in transactions]


@router.get("/stats", response_model=AccountStats)
def get_stats(db: Session = Depends(get_db)):
    return repository.get_stats(db)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    t = repository.get_by_id(db, transaction_id)
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.from_orm_model(t)


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    t = repository.create(db, data)
    return TransactionResponse.from_orm_model(t)


@router.post("/analyse-all")
def analyse_all(db: Session = Depends(get_db)):
    unprocessed = repository.get_unprocessed(db)
    updated = 0
    for t in unprocessed:
        vendor_trust = service.assess_vendor_trust(t.vendor)
        score, label, explanation = service.calculate_risk(
            amount=t.amount,
            vendor_trust=vendor_trust,
            frequency=t.frequency_score or 0.5,
        )
        if t.category == "Uncategorised":
            category = service.categorise_transaction(t.vendor, t.description or "")
            repository.update_category(db, t.id, category)
        repository.update_risk(
            db=db,
            transaction_id=t.id,
            risk_score=score,
            risk_label=label,
            xai_explanation=explanation,
            is_anomaly=(label == "high"),
            is_processed=True,
        )
        updated += 1
    return {"message": f"Analysed {updated} transactions", "updated": updated}
