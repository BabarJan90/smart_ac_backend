from sqlalchemy.orm import Session
from typing import List, Optional
from features.documents.models import GeneratedDocument


def get_all(db: Session) -> List[GeneratedDocument]:
    return db.query(GeneratedDocument).order_by(GeneratedDocument.created_at.desc()).all()


def get_by_id(db: Session, doc_id: int) -> Optional[GeneratedDocument]:
    return db.query(GeneratedDocument).filter(GeneratedDocument.id == doc_id).first()


def create(db: Session, title: str, content: str, doc_type: str = "general") -> GeneratedDocument:
    doc = GeneratedDocument(title=title, content=content, doc_type=doc_type)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
