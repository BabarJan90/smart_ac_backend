from pydantic import BaseModel
from typing import Optional, List


class ReviewerAssistRequest(BaseModel):
    limit: int = 10
    risk_filter: Optional[str] = None


class ReviewerStatsDto(BaseModel):
    total_transactions: int
    total_value: float
    high_risk_count: int
    anomaly_count: int


class ReviewerAssistResponse(BaseModel):
    agent: str
    summary: str
    key_concerns: List[str]
    recommended_actions: List[str]
    risk_level: str
    stats: ReviewerStatsDto


# ── Junior Assist — matches Flutter JuniorAssistResultDto ──────────────────

class CategorizationDto(BaseModel):
    transaction_id: Optional[int]
    vendor: Optional[str]
    category: Optional[str]
    confidence: Optional[float]
    notes: Optional[str]


class JuniorAssistResponse(BaseModel):
    status: str                            # Flutter expects 'status'
    processed: int                         # Flutter expects 'processed'
    categorisations: List[CategorizationDto]  # Flutter expects list


# ── Generate letter — matches Flutter ClientLetterResultDto ────────────────

class GenerateLetterRequest(BaseModel):
    client_name: str
    transaction_limit: int = 50


class ClientLetterResponse(BaseModel):
    status: str
    client: Optional[str]
    letter: Optional[str]


# ── Anomaly report — matches Flutter AnomalyReportResultDto ───────────────

class AnomalyReportResponse(BaseModel):
    status: str
    report: Optional[str]
