import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List
from core.email import send_high_risk_alert, send_report_ready
from features.transactions import repository as tx_repo
from features.transactions import service as tx_service
from features.agents import service as agent_service
from features.documents import repository as doc_repo
from features.audit import repository as audit_repo
from features.orchestrator.schemas import (
    OrchestratorResponse, OrchestratorAccountStateDto,
    OrchestratorPlanStepDto, OrchestratorActionLogDto,
    OrchestratorResultsDto, JuniorAssistResultDto, ReviewerAssistDto,
    ReviewerStatsDto, AnomalyReportResultDto, ClientLetterResultDto,
    CategorizationDto,
)


async def run(db: Session, client_name: str) -> OrchestratorResponse:
    start_time = time.time()
    action_log: List[OrchestratorActionLogDto] = []
    plan_executed: List[OrchestratorPlanStepDto] = []

    def log(action: str, detail: str):
        action_log.append(OrchestratorActionLogDto(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            detail=detail,
        ))

    # ── SENSE ──────────────────────────────────────────────────────────────
    all_transactions = tx_repo.get_all(db, limit=200)
    unprocessed      = tx_repo.get_unprocessed(db)

    # Refresh high-risk + anomalies after scoring
    high_risk  = tx_repo.get_high_risk(db)
    anomalies  = tx_repo.get_anomalies(db)
    total_value = sum(t.amount for t in all_transactions)

    log("SENSE", (
        f"Found {len(all_transactions)} transactions, "
        f"{len(unprocessed)} unprocessed, "
        f"{len(high_risk)} high-risk"
    ))
    audit_repo.log(db, action="orchestrator_sense",
                   details=f"Sensed {len(all_transactions)} transactions")

    # ── PLAN ───────────────────────────────────────────────────────────────
    priority = 1

    # Always run fuzzy risk scoring if there are unprocessed transactions
    if unprocessed:
        plan_executed.append(OrchestratorPlanStepDto(
            agent="Fuzzy Risk Scoring",
            reason=f"{len(unprocessed)} transactions need risk assessment",
            priority=priority,
        ))
        priority += 1
        plan_executed.append(OrchestratorPlanStepDto(
            agent="Junior Assist",
            reason=f"{len(unprocessed)} transactions need AI categorisation",
            priority=priority,
        ))
        priority += 1

    if high_risk or anomalies or unprocessed:
        plan_executed.append(OrchestratorPlanStepDto(
            agent="Reviewer Assist",
            reason="Review all transactions and flag concerns",
            priority=priority,
        ))
        priority += 1

    if anomalies or unprocessed:
        plan_executed.append(OrchestratorPlanStepDto(
            agent="Generate Anomaly Report",
            reason="Produce formal report of flagged transactions",
            priority=priority,
        ))
        priority += 1

    if client_name and client_name != "Unknown Client":
        plan_executed.append(OrchestratorPlanStepDto(
            agent="Generate Letter",
            reason=f"Client letter requested for {client_name}",
            priority=priority,
        ))

    log("PLAN", f"Planned {len(plan_executed)} actions: "
        f"{', '.join(p.agent for p in plan_executed)}")

    # ── ACT ────────────────────────────────────────────────────────────────
    results = OrchestratorResultsDto()

    # 1. Fuzzy Risk Scoring — score ALL unprocessed transactions
    if any(p.agent == "Fuzzy Risk Scoring" for p in plan_executed):
        scored = 0
        for t in unprocessed:
            vendor_trust = tx_service.assess_vendor_trust(t.vendor)
            score, label, explanation = tx_service.calculate_risk(
                amount=t.amount,
                vendor_trust=vendor_trust,
                frequency=t.frequency_score or 0.5,
            )
            if t.category in ("Uncategorised", None):
                category = tx_service.categorise_transaction(
                    t.vendor, t.description or ""
                )
                tx_repo.update_category(db, t.id, category)

            tx_repo.update_risk(
                db=db,
                transaction_id=t.id,
                risk_score=score,
                risk_label=label,
                xai_explanation=explanation,
                is_anomaly=(label == "high"),
                is_processed=True,
            )
            scored += 1

        # Re-fetch after scoring so counts are accurate
        high_risk = tx_repo.get_high_risk(db)
        anomalies  = tx_repo.get_anomalies(db)
        medium     = tx_repo.get_all(db, risk_filter="medium")

        log("ACT", (
            f"Fuzzy scoring complete: {scored} transactions scored. "
            f"High: {len(high_risk)}, "
            f"Medium: {len(medium)}, "
            f"Anomalies: {len(anomalies)}"
        ))

    # 2. Junior Assist — AI categorisation
    if any(p.agent == "Junior Assist" for p in plan_executed):
        categorisations = []
        # Re-fetch unprocessed (some may now be processed after fuzzy scoring)
        still_uncategorised = [
            t for t in tx_repo.get_all(db, limit=200)
            if t.category in ("Uncategorised", "General Expenses", None)
        ]
        for t in still_uncategorised[:10]:
            result = await agent_service.junior_assist(t.__dict__)
            tx_repo.update_category(db, t.id, result.get("category", t.category))
            categorisations.append(CategorizationDto(
                transaction_id=t.id,
                vendor=t.vendor,
                category=result.get("category"),
                confidence=result.get("confidence"),
                notes=result.get("notes"),
            ))
            audit_repo.log(db, action="junior_assist", entity_id=t.id,
                           details=f"Category: {result.get('category')}")

        results.junior_assist = JuniorAssistResultDto(
            status="success",
            processed=len(categorisations),
            categorisations=categorisations,
        )
        log("ACT", f"Junior Assist categorised {len(categorisations)} transactions")

    # 3. Reviewer Assist
    if any(p.agent == "Reviewer Assist" for p in plan_executed):
        all_transactions = tx_repo.get_all(db, limit=200)
        tx_dicts = [t.__dict__ for t in all_transactions]
        review = await agent_service.reviewer_assist(tx_dicts)
        raw_stats = review.get("stats", {})
        results.reviewer_assist = ReviewerAssistDto(
            agent=review.get("agent", "Reviewer Assist"),
            summary=review.get("summary", ""),
            key_concerns=review.get("key_concerns", []),
            recommended_actions=review.get("recommended_actions", []),
            risk_level=review.get("risk_level", "low"),
            stats=ReviewerStatsDto(
                total_transactions=raw_stats.get("total_transactions", 0),
                total_value=raw_stats.get("total_value", 0.0),
                high_risk_count=raw_stats.get("high_risk_count", 0),
                anomaly_count=raw_stats.get("anomaly_count", 0),
            ),
        )
        log("ACT", f"Reviewer Assist complete. Risk: {review.get('risk_level')}")

    # 4. Anomaly Report
    if any(p.agent == "Generate Anomaly Report" for p in plan_executed):
        anomaly_dicts = [t.__dict__ for t in anomalies]
        report = await agent_service.generate_anomaly_report(anomaly_dicts)
        doc_repo.create(db, title="Anomaly Detection Report",
                        content=report, doc_type="anomaly_report")
        results.anomaly_report = AnomalyReportResultDto(
            status="success",
            report=report,
        )
        log("ACT", f"Anomaly report generated for {len(anomalies)} flagged transactions")
        
        # Send ONE high risk alert email
        if high_risk:
            high_risk_dicts = [t.__dict__ for t in high_risk]
            email_sent = send_high_risk_alert(
                high_risk_transactions=high_risk_dicts,
                anomaly_count=len(anomalies),
                report_content=report,
                client_name=client_name,
            )
            if email_sent:
                log("ACT", f"High risk alert email sent for {len(high_risk)} transactions")
                audit_repo.log(db, action="email_alert_sent",
                            details=f"High risk alert sent: {len(high_risk)} transactions")

    # 5. Generate Letter
    if any(p.agent == "Generate Letter" for p in plan_executed):
        all_transactions = tx_repo.get_all(db, limit=200)
        tx_dicts = [t.__dict__ for t in all_transactions]
        review_data = results.reviewer_assist.model_dump() \
            if results.reviewer_assist else None
        letter = await agent_service.generate_client_letter(
            client_name, tx_dicts, review_data
        )
        doc_repo.create(db, title=f"Client Letter — {client_name}",
                        content=letter, doc_type="client_letter")
        results.client_letter = ClientLetterResultDto(
            status="success",
            client=client_name,
            letter=letter,
        )
        log("ACT", f"Client letter generated for {client_name}")

    # ── REPORT ─────────────────────────────────────────────────────────────
    duration = round(time.time() - start_time, 2)
    high_risk  = tx_repo.get_high_risk(db)
    anomalies  = tx_repo.get_anomalies(db)
    all_transactions = tx_repo.get_all(db, limit=200)
    total_value = sum(t.amount for t in all_transactions)

    summary = (
        f"Orchestrator completed {len(action_log)} actions for {client_name} "
        f"in {duration}s. Processed {len(all_transactions)} transactions, "
        f"identified {len(high_risk)} high-risk items and "
        f"{len(anomalies)} anomalies."
    )
    log("REPORT", summary)
    audit_repo.log(db, action="orchestrator_complete", details=summary)

    return OrchestratorResponse(
        orchestrator="Orchestrator",
        completed_at=datetime.now(timezone.utc).isoformat(),
        duration_seconds=duration,
        summary=summary,
        account_state=OrchestratorAccountStateDto(
            total_transactions=len(all_transactions),
            total_value=round(total_value, 2),
            high_risk_count=len(high_risk),
            anomaly_count=len(anomalies),
        ),
        plan_executed=plan_executed,
        action_log=action_log,
        results=results,
    )