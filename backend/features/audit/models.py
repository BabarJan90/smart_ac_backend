from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id         = Column(Integer, primary_key=True, index=True)
    action     = Column(String, nullable=False)
    entity_id  = Column(Integer, nullable=True)
    details    = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
