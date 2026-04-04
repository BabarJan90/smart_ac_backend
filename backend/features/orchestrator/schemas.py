from pydantic import BaseModel
from typing import Optional, List


class OrchestratorRequest(BaseModel):
    client_name: Optional[str] = "Unknown Client"


# ── Nested shapes matching Flutter exactly ─────────────────────────────────

class OrchestratorAccountStateDto(BaseModel):
    total_transactions: int
    total_value: float
    high_risk_count: int
    anomaly_count: int


class OrchestratorPlanStepDto(BaseModel):
    agent: str
    reason: str
    priority: int


class OrchestratorActionLogDto(BaseModel):
    timestamp: str
    action: str
    detail: str


class CategorizationDto(BaseModel):
    transaction_id: Optional[int]
    vendor: Optional[str]
    category: Optional[str]
    confidence: Optional[float]
    notes: Optional[str]


class JuniorAssistResultDto(BaseModel):
    status: str
    processed: int
    categorisations: List[CategorizationDto]


class ReviewerStatsDto(BaseModel):
    total_transactions: int
    total_value: float
    high_risk_count: int
    anomaly_count: int


class ReviewerAssistDto(BaseModel):
    agent: str
    summary: str
    key_concerns: List[str]
    recommended_actions: List[str]
    risk_level: str
    stats: ReviewerStatsDto


class AnomalyReportResultDto(BaseModel):
    status: str
    report: Optional[str]


class ClientLetterResultDto(BaseModel):
    status: str
    client: Optional[str]
    letter: Optional[str]


class OrchestratorResultsDto(BaseModel):
    junior_assist: Optional[JuniorAssistResultDto] = None
    reviewer_assist: Optional[ReviewerAssistDto] = None
    anomaly_report: Optional[AnomalyReportResultDto] = None
    client_letter: Optional[ClientLetterResultDto] = None


# ── Top level — matches Flutter OrchestratorResultDto exactly ──────────────

class OrchestratorResponse(BaseModel):
    orchestrator: str                          # Flutter expects 'orchestrator' not 'agent'
    completed_at: str                          # Flutter expects this
    duration_seconds: float                    # Flutter expects this
    summary: str
    account_state: OrchestratorAccountStateDto
    plan_executed: List[OrchestratorPlanStepDto]
    action_log: List[OrchestratorActionLogDto]
    results: OrchestratorResultsDto
