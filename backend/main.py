"""
SmartAC — AI-Powered Accounting Platform
KTP Demo: University of Essex × Active Software Platform UK Ltd

Entry point — registers all feature routers and starts the app.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION
from core.database import create_tables, SessionLocal

# ── Import all models so create_tables() sees them ────────────────────────
from features.transactions.models import Transaction         # noqa: F401
from features.documents.models import GeneratedDocument      # noqa: F401
from features.audit.models import AuditLog                   # noqa: F401

# ── Import all routers ─────────────────────────────────────────────────────
from features.transactions.router import router as transactions_router
from features.agents.router import router as agents_router
from features.orchestrator.router import router as orchestrator_router
from features.documents.router import router as documents_router
from features.audit.router import router as audit_router

from db.seed import seed

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ───────────────────────────────────────────────────────
app.include_router(transactions_router)
app.include_router(agents_router)
app.include_router(orchestrator_router)
app.include_router(documents_router)
app.include_router(audit_router)


# ── Startup ────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    create_tables()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


# ── Health check ───────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "project": "SmartAC",
        "description": APP_DESCRIPTION,
        "university": "University of Essex",
        "company": "Active Software Platform UK Ltd",
        "endpoints": {
            "transactions":      "/transactions",
            "stats":             "/transactions/stats",
            "analyse_all":       "/transactions/analyse-all",
            "junior_assist":     "/agents/junior-assist/{id}",
            "reviewer_assist":   "/agents/reviewer-assist",
            "orchestrate":       "/agents/orchestrate",
            "generate_letter":   "/agents/generate-letter",
            "anomaly_report":    "/agents/generate-anomaly-report",
            "documents":         "/agents/documents",
            "audit_log":         "/agents/audit-log",
            "docs":              "/docs",
        }
    }
