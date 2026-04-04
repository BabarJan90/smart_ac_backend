from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class TransactionCreate(BaseModel):
    vendor: str
    amount: float
    description: Optional[str] = None
    category: Optional[str] = "Uncategorised"
    date: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    vendor: str
    amount: float
    description: Optional[str]
    category: str
    date: Optional[str] = ""
    risk_score: Optional[float]
    risk_label: Optional[str]
    explanation: Optional[str] = None     # Flutter expects 'explanation' not 'xai_explanation'
    is_anomaly: bool
    is_processed: bool
    created_at: Optional[datetime]

    @classmethod
    def from_orm_model(cls, t):
        return cls(
            id=t.id,
            vendor=t.vendor,
            amount=t.amount,
            description=t.description,
            category=t.category,
            date=t.date or "",
            risk_score=t.risk_score,
            risk_label=t.risk_label,
            explanation=t.xai_explanation,   # map xai_explanation → explanation
            is_anomaly=t.is_anomaly,
            is_processed=t.is_processed,
            created_at=t.created_at,
        )

    class Config:
        from_attributes = True


class RiskDistribution(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    unscored: int = 0


class AccountStats(BaseModel):
    total_transactions: int
    total_value: float
    risk_distribution: RiskDistribution
    anomaly_count: int
