from sqlalchemy.orm import Session
from typing import List, Optional
from features.audit.models import AuditLog


def get_all(db: Session, skip: int = 0, limit: int = 50) -> List[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def log(
    db: Session,
    action: str,
    entity_id: Optional[int] = None,
    details: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(action=action, entity_id=entity_id, details=details)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
