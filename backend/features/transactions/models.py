"""
Transaction database model.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from core.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(Integer, primary_key=True, index=True)
    vendor      = Column(String, nullable=False)
    amount      = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    category    = Column(String, default="Uncategorised")
    date        = Column(String, nullable=True)

    # Fuzzy risk scoring
    risk_score      = Column(Float, nullable=True)
    risk_label      = Column(String, nullable=True)   # low / medium / high
    xai_explanation = Column(Text, nullable=True)
    vendor_trust    = Column(Float, default=0.5)
    frequency_score = Column(Float, default=0.5)

    # AI processing flags
    is_anomaly      = Column(Boolean, default=False)
    is_processed    = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
