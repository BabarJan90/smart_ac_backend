from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from features.transactions.models import Transaction
from features.transactions.schemas import TransactionCreate, AccountStats, RiskDistribution


def get_all(db: Session, limit: int = 100, risk_filter: Optional[str] = None) -> List[Transaction]:
    query = db.query(Transaction)
    if risk_filter:
        query = query.filter(Transaction.risk_label == risk_filter)
    return query.order_by(Transaction.created_at.desc()).limit(limit).all()


def get_by_id(db: Session, transaction_id: int) -> Optional[Transaction]:
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def get_unprocessed(db: Session) -> List[Transaction]:
    return db.query(Transaction).filter(Transaction.is_processed == False).all()


def get_high_risk(db: Session) -> List[Transaction]:
    return db.query(Transaction).filter(Transaction.risk_label == "high").all()


def get_anomalies(db: Session) -> List[Transaction]:
    return db.query(Transaction).filter(Transaction.is_anomaly == True).all()


def create(db: Session, data: TransactionCreate) -> Transaction:
    transaction = Transaction(**data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def update_risk(
    db: Session,
    transaction_id: int,
    risk_score: float,
    risk_label: str,
    xai_explanation: str,
    is_anomaly: bool = False,
    is_processed: bool = True,
) -> Optional[Transaction]:
    t = get_by_id(db, transaction_id)
    if not t:
        return None
    t.risk_score = risk_score
    t.risk_label = risk_label
    t.xai_explanation = xai_explanation
    t.is_anomaly = is_anomaly
    t.is_processed = is_processed
    db.commit()
    db.refresh(t)
    return t


def update_category(db: Session, transaction_id: int, category: str) -> Optional[Transaction]:
    t = get_by_id(db, transaction_id)
    if not t:
        return None
    t.category = category
    db.commit()
    db.refresh(t)
    return t


def get_stats(db: Session) -> AccountStats:
    total = db.query(func.count(Transaction.id)).scalar() or 0
    total_value = db.query(func.sum(Transaction.amount)).scalar() or 0.0
    high = db.query(func.count(Transaction.id)).filter(Transaction.risk_label == "high").scalar() or 0
    medium = db.query(func.count(Transaction.id)).filter(Transaction.risk_label == "medium").scalar() or 0
    low = db.query(func.count(Transaction.id)).filter(Transaction.risk_label == "low").scalar() or 0
    unscored = db.query(func.count(Transaction.id)).filter(Transaction.risk_label == None).scalar() or 0
    anomalies = db.query(func.count(Transaction.id)).filter(Transaction.is_anomaly == True).scalar() or 0

    return AccountStats(
        total_transactions=total,
        total_value=round(total_value, 2),
        risk_distribution=RiskDistribution(
            low=low,
            medium=medium,
            high=high,
            unscored=unscored,
        ),
        anomaly_count=anomalies,
    )
