from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from features.orchestrator import service
from features.orchestrator.schemas import OrchestratorRequest

router = APIRouter(prefix="/agents", tags=["Orchestrator"])


@router.post("/orchestrate")
async def orchestrate(request: OrchestratorRequest, db: Session = Depends(get_db)):
    """
    Run the full Orchestrator Agent — Sense → Plan → Act → Report.
    Autonomously decides which AI workstreams to run.
    """
    return await service.run(db, client_name=request.client_name)
