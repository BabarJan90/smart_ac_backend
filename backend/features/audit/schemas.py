from pydantic import BaseModel
from datetime import datetime
from typing import Optional

MODEL_USED = "claude-haiku-4-5-20251001"


class AuditEntryResponse(BaseModel):
    id: int
    timestamp: str                    # Flutter expects 'timestamp' not 'created_at'
    action: str
    transaction_id: Optional[int]     # Flutter expects 'transaction_id' not 'entity_id'
    model_used: Optional[str]         # Flutter expects this field
    justification: Optional[str]      # Flutter expects 'justification' not 'details'

    @classmethod
    def from_orm_model(cls, entry):
        return cls(
            id=entry.id,
            timestamp=entry.created_at.isoformat() if entry.created_at else "",
            action=entry.action,
            transaction_id=entry.entity_id,       # map entity_id → transaction_id
            model_used=MODEL_USED,
            justification=entry.details,           # map details → justification
        )
