"""
SmartAC - LangChain Orchestrator
Alternative to the custom Sense→Plan→Act→Report orchestrator.
Uses LangGraph ReAct agent + Claude to autonomously decide which agents to run.
"""
import asyncio
from sqlalchemy.orm import Session
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from core.config import ANTHROPIC_API_KEY

from features.transactions import repository as tx_repo
from features.transactions import service as tx_service
from features.agents import service as agent_service
from features.documents import repository as doc_repo
from features.audit import repository as audit_repo
from core.email import send_high_risk_alert
from datetime import datetime, timezone


def run_langchain_orchestrator(db: Session, client_name: str = "Valued Client") -> dict:
    """
    LangChain-powered orchestrator.
    Claude autonomously decides which agents to run based on account state.
    """

    started_at = datetime.now(timezone.utc)

    # ── Get account context ────────────────────────────────────────────────
    transactions = tx_repo.get_all(db, limit=100)
    stats = tx_repo.get_stats(db)
    action_log = []

    # ── Define tools ───────────────────────────────────────────────────────

    @tool
    def run_fuzzy_scoring() -> str:
        """Run fuzzy logic risk scoring on all unscored transactions.
        Always run this first before any other agent."""
        unprocessed = tx_repo.get_unprocessed(db)
        count = 0
        for t in unprocessed:
            vendor_trust = tx_service.assess_vendor_trust(t.vendor)
            frequency = t.frequency_score or 0.5
            score, label, explanation = tx_service.calculate_risk(
                t.amount, vendor_trust, frequency
            )
            tx_repo.update_risk(db, t.id, score, label, explanation)
            count += 1
        action_log.append(f"Fuzzy scoring: {count} transactions scored")
        return f"Scored {count} transactions with fuzzy logic"

    @tool
    def run_junior_assist() -> str:
        """Categorise all unprocessed transactions using AI.
        Run after fuzzy scoring."""
        unprocessed = tx_repo.get_unprocessed(db)
        count = 0
        for t in unprocessed[:20]:
            result = asyncio.run(
                agent_service.junior_assist(t.__dict__)
            )
            tx_repo.update_category(db, t.id, result.get("category", t.category))
            count += 1
        action_log.append(f"Junior assist: {count} transactions categorised")
        return f"Categorised {count} transactions"

    @tool
    def run_reviewer_assist() -> str:
        """Review high risk transactions in batch.
        Only run if high risk transactions exist."""
        tx_dicts = [t.__dict__ for t in transactions]
        result = asyncio.run(
            agent_service.reviewer_assist(tx_dicts)
        )
        action_log.append(f"Reviewer: risk level {result.get('risk_level')}")
        return f"Review complete. Risk level: {result.get('risk_level')}. Key concerns: {result.get('key_concerns', [])}"

    @tool
    def run_anomaly_report() -> str:
        """Generate anomaly detection report.
        Only run if anomalies are detected."""
        anomalies = tx_repo.get_anomalies(db)
        if not anomalies:
            return "No anomalies found"
        anomaly_dicts = [t.__dict__ for t in anomalies]
        report = asyncio.run(
            agent_service.generate_anomaly_report(anomaly_dicts)
        )
        doc_repo.create(db, title="Anomaly Report (LangChain)",
                        content=report, doc_type="anomaly_report")
        action_log.append(f"Anomaly report generated for {len(anomalies)} anomalies")
        return f"Anomaly report generated for {len(anomalies)} anomalies"

    @tool
    def send_alert_email() -> str:
        """Send high risk alert email to accountant.
        Only run if high risk transactions exist."""
        anomalies = tx_repo.get_anomalies(db)
        if not anomalies:
            return "No high risk items — email not sent"
        send_high_risk_alert(
            high_risk_transactions=[t.__dict__ for t in anomalies],
            anomaly_count=len(anomalies),
            report_content="High risk transactions detected by LangChain orchestrator",
        )
        action_log.append("Email alert sent to accountant")
        return "High risk alert email sent"

    @tool
    def generate_client_letter() -> str:
        """Generate professional client letter summarising account analysis.
        Always run this last."""
        tx_dicts = [t.__dict__ for t in transactions]
        letter = asyncio.run(
            agent_service.generate_client_letter(client_name, tx_dicts)
        )
        doc_repo.create(db, title=f"Client Letter — {client_name} (LangChain)",
                        content=letter, doc_type="client_letter")
        action_log.append(f"Client letter generated for {client_name}")
        return "Client letter generated successfully"

    # ── Build agent ────────────────────────────────────────────────────────

    tools = [
        run_fuzzy_scoring,
        run_junior_assist,
        run_reviewer_assist,
        run_anomaly_report,
        send_alert_email,
        generate_client_letter,
    ]

    # llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=4096)
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        api_key=ANTHROPIC_API_KEY,
    )

    system_prompt = f"""You are an autonomous AI accounting agent for SmartAC.

Current account state:
- Total transactions: {stats.total_transactions}
- High risk count: {stats.risk_distribution.high}
- Anomaly count: {stats.anomaly_count}
- Unprocessed: {stats.risk_distribution.unscored}
- Client: {client_name}

Your job is to analyse the account and run the appropriate agents in the right order.
Always start with fuzzy scoring first, then categorise, then review if needed.
Only run agents that are necessary based on the account state.
Always end with generating a client letter."""

    agent = create_react_agent(llm, tools, prompt=system_prompt)

    result = agent.invoke({
        "messages": [("human", "Analyse and process all transactions for this account.")]
    })

    # ── Log to audit ───────────────────────────────────────────────────────
    audit_repo.log(db, action="langchain_orchestrator",
                   details=f"LangChain orchestrator completed. Actions: {len(action_log)}")

    # ── Extract final message ──────────────────────────────────────────────
    final_message = ""
    if result.get("messages"):
        final_message = result["messages"][-1].content

    completed_at = datetime.now(timezone.utc).isoformat()
    duration = round((datetime.now(timezone.utc) - started_at).total_seconds(), 2)

    return {
        "orchestrator": "LangChain + Claude (LangGraph ReAct)",
        "completed_at": completed_at,
        "duration_seconds": duration,
        "summary": final_message,
        "account_state": {
            "total_transactions": stats.total_transactions,
            "total_value": stats.total_value,
            "high_risk_count": stats.risk_distribution.high,
            "anomaly_count": stats.anomaly_count,
        },
        "plan_executed": [
            {"agent": log, "reason": "Decided by Claude autonomously", "priority": i + 1}
            for i, log in enumerate(action_log)
        ],
        "action_log": [
            {
                "timestamp": completed_at,
                "action": "ACT",
                "detail": log,
            }
            for log in action_log
        ],
        "results": {
            "junior_assist": None,
            "reviewer_assist": None,
            "anomaly_report": None,
            "client_letter": None,
        }
        
    }