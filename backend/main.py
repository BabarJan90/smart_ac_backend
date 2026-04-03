"""
AccountIQ — AI Engineer in Accounting KTP Demo Project
University of Essex × Active Software Platform UK Ltd

FastAPI backend serving all AI workstreams:
- Fuzzy Logic + XAI risk scoring
- NLP entity extraction
- Junior Assist agent
- Reviewer Assist agent
- Generative AI document creation
- GDPR audit trail
"""
from backend.routers import agents
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db
from db.seed import seed_transactions
from routers import transactions

app = FastAPI(
    title="AccountIQ API",
    description="AI-powered accounting analysis — KTP Demo",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production: restrict to your Flutter app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(agents.router)


@app.on_event("startup")
async def startup():
    init_db()
    seed_transactions(n=50)
    # Auto-score all seeded transactions on first run
    from db.database import SessionLocal, Transaction
    from services.fuzzy_risk import fuzzy_scorer
    from services.nlp_service import nlp_service
    db = SessionLocal()
    try:
        unscored = db.query(Transaction).filter(Transaction.risk_score == None).all()
        for tx in unscored:
            risk_score, risk_label, explanation = fuzzy_scorer.score(tx.amount, tx.vendor)
            tx.risk_score = risk_score
            tx.risk_label = risk_label
            tx.is_anomaly = risk_score > 70
            tx.explanation = explanation
            tx.category = nlp_service.classify_transaction(
                tx.vendor, tx.description or "", tx.amount
            )
        db.commit()
        print(f"Auto-scored {len(unscored)} transactions on startup.")
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "project": "AccountIQ",
        "description": "AI Engineer in Accounting — KTP Demo",
        "university": "University of Essex",
        "company": "Active Software Platform UK Ltd",
        "endpoints": {
            "transactions": "/transactions",
            "stats": "/transactions/stats",
            "analyse_all": "/transactions/analyse-all",
            "junior_assist": "/agents/junior-assist/{id}",
            "reviewer_assist": "/agents/reviewer-assist",
            "generate_letter": "/agents/generate-letter",
            "anomaly_report": "/agents/generate-anomaly-report",
            "audit_log": "/agents/audit-log",
            "docs": "/docs",
        }
    }


@app.get("/health")
def health():
    return {"status": "ok"}
