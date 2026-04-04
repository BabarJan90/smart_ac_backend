from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from core.database import Base


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id         = Column(Integer, primary_key=True, index=True)
    title      = Column(String, nullable=False)
    content    = Column(Text, nullable=False)
    doc_type   = Column(String, default="general")   # client_letter / anomaly_report
    created_at = Column(DateTime(timezone=True), server_default=func.now())
