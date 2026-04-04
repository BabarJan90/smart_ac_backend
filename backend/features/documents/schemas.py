from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentResponse(BaseModel):
    id: int
    doc_type: str
    created_at: str                   # Flutter expects String not datetime
    preview: Optional[str] = None     # Flutter expects this field
    content: Optional[str] = None

    @classmethod
    def from_orm_model(cls, doc):
        content = doc.content or ""
        return cls(
            id=doc.id,
            doc_type=doc.doc_type,
            created_at=doc.created_at.isoformat() if doc.created_at else "",
            preview=content[:150] + "..." if len(content) > 150 else content,
            content=content,
        )


class DocumentSummary(BaseModel):
    id: int
    doc_type: str
    created_at: str
    preview: Optional[str] = None

    @classmethod
    def from_orm_model(cls, doc):
        content = doc.content or ""
        return cls(
            id=doc.id,
            doc_type=doc.doc_type,
            created_at=doc.created_at.isoformat() if doc.created_at else "",
            preview=content[:150] + "..." if len(content) > 150 else content,
        )
