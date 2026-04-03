"""
Orchestrator Agent — the brain of AccountIQ.

This is what makes the system truly Agentic AI.
Instead of a human triggering each agent manually,
the Orchestrator autonomously:
  1. Assesses the current state of the accounts
  2. Makes a plan — deciding which agents to run and in what order
  3. Executes each agent in sequence
  4. Reacts to what each agent finds
  5. Produces a final report of everything it did

This maps directly to the KTP requirement:
"Researching and developing an Agentic AI Management System"
"""

import json
from typing import Dict, List
from datetime import datetime
from backend.services.agent_service_with_ollama import (
    junior_assist_categorise,
    reviewer_assist_analyse,
    generate_client_letter,
    generate_anomaly_report,
    _ollama_generate,
)


class OrchestratorAgent:
    """
    The master agent that coordinates all other agents autonomously.
    
    It follows a Sense → Plan → Act → Report cycle:
    - Sense:  Look at the current state of the database
    - Plan:   Decide what needs to be done
    - Act:    Run the appropriate agents in order
    - Report: Summarise everything that happened
    """

    def __init__(self):
        self.action_log = []   # Everything the orchestrator does is logged
        self.start_time = None

    def _log(self, action: str, detail: str = ""):
        """Log every decision the orchestrator makes — this is the XAI component."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "detail": detail,
        }
        self.action_log.append(entry)
        print(f"[Orchestrator] {action}: {detail}")

    # ── PHASE 1: SENSE ────────────────────────────────────────────────────────

    def sense(self, transactions: List[Dict]) -> Dict:
        """
        Assess the current state of the accounts.
        Returns a state dictionary the planner uses to make decisions.
        """
        self._log("Sensing", f"Analysing {len(transactions)} transactions")

        uncategorised = [t for t in transactions if not t.get("category")
                         or t.get("category") == "Uncategorised"]
        unscored = [t for t in transactions if t.get("risk_score") is None]
        high_risk = [t for t in transactions if t.get("risk_label") == "high"]
        anomalies = [t for t in transactions if t.get("is_anomaly")]
        total_value = sum(t.get("amount", 0) for t in transactions)

        state = {
            "total_transactions": len(transactions),
            "total_value": round(total_value, 2),
            "uncategorised_count": len(uncategorised),
            "unscored_count": len(unscored),
            "high_risk_count": len(high_risk),
            "anomaly_count": len(anomalies),
            "uncategorised": uncategorised[:5],    # first 5 for processing
            "high_risk": high_risk,
            "anomalies": anomalies,
            "all_transactions": transactions,
        }

        self._log("Sense complete", (
            f"Found {len(uncategorised)} uncategorised, "
            f"{len(high_risk)} high-risk, "
            f"{len(anomalies)} anomalies"
        ))
        return state

    # ── PHASE 2: PLAN ─────────────────────────────────────────────────────────

    def plan(self, state: Dict, client_name: str = None) -> List[Dict]:
        """
        Autonomously decide what agents to run based on the current state.
        This is the key differentiator from simple automation —
        the AI decides the plan, not the human.
        """
        self._log("Planning", "Deciding which agents to run")
        plan = []

        # Decision 1: Are there uncategorised transactions?
        if state["uncategorised_count"] > 0:
            plan.append({
                "agent": "Junior Assist",
                "reason": f"{state['uncategorised_count']} transactions need categorising",
                "priority": 1,
            })
            self._log("Decision", "Junior Assist needed — uncategorised transactions found")
        else:
            self._log("Decision", "Junior Assist skipped — all transactions categorised")

        # Decision 2: Are there high risk or anomalous transactions?
        if state["high_risk_count"] > 0 or state["anomaly_count"] > 0:
            plan.append({
                "agent": "Reviewer Assist",
                "reason": (
                    f"{state['high_risk_count']} high-risk and "
                    f"{state['anomaly_count']} anomalous transactions need review"
                ),
                "priority": 2,
            })
            self._log("Decision", "Reviewer Assist needed — risks detected")
        else:
            self._log("Decision", "Reviewer Assist skipped — no high-risk transactions")

        # Decision 3: Are there anomalies that need a formal report?
        if state["anomaly_count"] > 0:
            plan.append({
                "agent": "Anomaly Report",
                "reason": f"{state['anomaly_count']} anomalies require formal documentation",
                "priority": 3,
            })
            self._log("Decision", "Anomaly Report needed — anomalies found")

        # Decision 4: Is a client letter requested?
        if client_name:
            plan.append({
                "agent": "Generative AI",
                "reason": f"Client letter requested for {client_name}",
                "priority": 4,
            })
            self._log("Decision", f"Generative AI needed — letter for {client_name}")

        # Sort by priority
        plan.sort(key=lambda x: x["priority"])
        self._log("Plan complete", f"{len(plan)} agents will run: "
                  f"{[p['agent'] for p in plan]}")
        return plan

    # ── PHASE 3: ACT ──────────────────────────────────────────────────────────

    async def act(self, plan: List[Dict], state: Dict,
                  client_name: str = None) -> Dict:
        """
        Execute the plan — run each agent in order.
        Each agent's output can influence what the next agent does.
        """
        results = {}

        for step in plan:
            agent_name = step["agent"]
            self._log(f"Running {agent_name}", step["reason"])

            try:
                if agent_name == "Junior Assist":
                    # Run Junior Assist on uncategorised transactions
                    categorised = []
                    for tx in state["uncategorised"][:3]:  # limit for speed
                        result = await junior_assist_categorise(tx)
                        categorised.append({
                            "transaction_id": tx.get("id"),
                            "vendor": tx.get("vendor"),
                            "category": result.get("category"),
                            "confidence": result.get("confidence"),
                            "notes": result.get("notes"),
                        })
                    results["junior_assist"] = {
                        "status": "completed",
                        "processed": len(categorised),
                        "categorisations": categorised,
                    }
                    self._log("Junior Assist complete",
                              f"Categorised {len(categorised)} transactions")

                elif agent_name == "Reviewer Assist":
                    # Run Reviewer Assist — it gets richer context if
                    # Junior Assist already ran
                    tx_list = [
                        {
                            "id": t.get("id"),
                            "vendor": t.get("vendor"),
                            "amount": t.get("amount"),
                            "risk_label": t.get("risk_label"),
                            "risk_score": t.get("risk_score"),
                            "is_anomaly": t.get("is_anomaly"),
                            "explanation": t.get("explanation"),
                        }
                        for t in state["all_transactions"][:10]
                    ]
                    review = await reviewer_assist_analyse(tx_list)
                    results["reviewer_assist"] = review

                    # Orchestrator reacts: if risk is high, escalate
                    if review.get("risk_level") == "high":
                        self._log("Escalation",
                                  "High risk detected — anomaly report will be prioritised")

                    self._log("Reviewer Assist complete",
                              f"Risk level: {review.get('risk_level')}")

                elif agent_name == "Anomaly Report":
                    anomaly_list = [
                        {
                            "id": t.get("id"),
                            "vendor": t.get("vendor"),
                            "amount": t.get("amount"),
                            "risk_score": t.get("risk_score"),
                            "explanation": t.get("explanation"),
                        }
                        for t in state["anomalies"][:5]
                    ]
                    report = await generate_anomaly_report(anomaly_list)
                    results["anomaly_report"] = {
                        "status": "completed",
                        "report": report,
                    }
                    self._log("Anomaly Report complete",
                              f"Report generated for {len(anomaly_list)} anomalies")

                elif agent_name == "Generative AI":
                    # Use review summary if available
                    review_summary = results.get("reviewer_assist")
                    letter = await generate_client_letter(
                        client_name,
                        state["all_transactions"][:10],
                        review_summary,
                    )
                    results["client_letter"] = {
                        "status": "completed",
                        "client": client_name,
                        "letter": letter,
                    }
                    self._log("Generative AI complete",
                              f"Letter generated for {client_name}")

            except Exception as e:
                self._log(f"{agent_name} failed", str(e))
                results[agent_name.lower().replace(" ", "_")] = {
                    "status": "failed",
                    "error": str(e),
                }

        return results

    # ── PHASE 4: REPORT ───────────────────────────────────────────────────────

    def report(self, state: Dict, plan: List[Dict], results: Dict) -> Dict:
        """
        Produce a final summary of everything the orchestrator did.
        This is what gets shown to the accountant.
        """
        self._log("Generating final report")

        duration = (datetime.utcnow() -
                    self.start_time).total_seconds() if self.start_time else 0

        return {
            "orchestrator": "AccountIQ Orchestrator v1.0",
            "completed_at": datetime.utcnow().isoformat(),
            "duration_seconds": round(duration, 2),
            "account_state": {
                "total_transactions": state["total_transactions"],
                "total_value": state["total_value"],
                "high_risk_count": state["high_risk_count"],
                "anomaly_count": state["anomaly_count"],
            },
            "plan_executed": plan,
            "results": results,
            "action_log": self.action_log,
            "summary": self._generate_summary(state, results),
        }

    def _generate_summary(self, state: Dict, results: Dict) -> str:
        """Plain English summary of what the orchestrator did."""
        parts = []

        if "junior_assist" in results:
            n = results["junior_assist"].get("processed", 0)
            parts.append(f"categorised {n} transactions automatically")

        if "reviewer_assist" in results:
            risk = results["reviewer_assist"].get("risk_level", "unknown")
            parts.append(f"reviewed accounts — overall risk level is {risk.upper()}")

        if "anomaly_report" in results:
            parts.append(f"generated anomaly report for "
                         f"{state['anomaly_count']} flagged transactions")

        if "client_letter" in results:
            client = results["client_letter"].get("client", "client")
            parts.append(f"generated client letter for {client}")

        if not parts:
            return "No actions were required — all accounts are in order."

        return "Orchestrator autonomously: " + ", ".join(parts) + "."

    # ── MAIN ENTRY POINT ──────────────────────────────────────────────────────

    async def run(self, transactions: List[Dict],
                  client_name: str = None) -> Dict:
        """
        Main entry point — runs the full Sense → Plan → Act → Report cycle.
        This is called with a goal, not a list of steps.
        """
        self.start_time = datetime.utcnow()
        self.action_log = []

        self._log("Orchestrator started",
                  f"Goal: analyse accounts"
                  + (f" and generate letter for {client_name}" if client_name else ""))

        # Sense → Plan → Act → Report
        state = self.sense(transactions)
        plan = self.plan(state, client_name)
        results = await self.act(plan, state, client_name)
        final_report = self.report(state, plan, results)

        self._log("Orchestrator complete",
                  f"Ran {len(plan)} agents in "
                  f"{final_report['duration_seconds']}s")

        return final_report


# Singleton instance
orchestrator = OrchestratorAgent()
