from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from features.documents import repository
from features.documents.schemas import DocumentResponse, DocumentSummary

router = APIRouter(prefix="/agents/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentSummary])
def get_documents(db: Session = Depends(get_db)):
    docs = repository.get_all(db)
    return [DocumentSummary.from_orm_model(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = repository.get_by_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_orm_model(doc)
