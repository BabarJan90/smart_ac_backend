from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from features.audit import repository
from features.audit.schemas import AuditEntryResponse

router = APIRouter(prefix="/agents/audit-log", tags=["Audit"])


@router.get("", response_model=List[AuditEntryResponse])
def get_audit_log(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    entries = repository.get_all(db, skip=skip, limit=limit)
    return [AuditEntryResponse.from_orm_model(e) for e in entries]
