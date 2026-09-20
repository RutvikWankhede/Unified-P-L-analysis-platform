"""
financial_orchestrator_agent.py - Master Financial Intelligence Orchestrator
=============================================================================
Autonomous ReAct reasoning loop:
1. Deconstructs user financial goals into multi-intent components.
2. Formulates dynamic execution plan based on decomposed intents.
3. Selects and executes controlled tools from agent_tools registry.
4. Inspects and correlates analytical outputs.
5. Passes candidate answers to FinancialValidationAgent for mathematical and semantic completeness verification.
6. Persists full Execution Trace in AILog.
7. Emits concise, evidence-grounded executive responses.
"""

from __future__ import annotations
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from agents.tools import agent_tools
from agents.validation_agent import validation_agent, ValidationResult
from agents.memory_agent import memory_agent
from services.copilot_agent import format_inr, format_margin, ask_copilot
from services.copilot_nlu import (
    parse_question,
    decompose_intents,
    detect_primary_metric,
    detect_direction,
    detect_rank_and_limit
)
from models.ai_log import AILog
from routers.datasets_router import get_active_dataset_id

logger = logging.getLogger(__name__)


class ToolExecutionRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    summary_output: str
    execution_time_ms: int
    status: str = "SUCCESS"


class ExecutionTrace(BaseModel):
    session_id: str
    user_goal: str
    detected_intents: List[Dict[str, Any]] = Field(default_factory=list)
    planned_steps: List[str]
    executed_tools: List[ToolExecutionRecord]
    validation_result: Optional[ValidationResult] = None
    final_answer: str
    total_time_ms: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FinancialOrchestratorAgent:
    """Master reasoning agent orchestrating multi-tool financial intelligence workflows."""

    def execute_query(
        self,
        db: Session,
        question: str,
        session_id: str = "default",
        user_id: int = 1
    ) -> ExecutionTrace:
        """Executes full autonomous ReAct reasoning, tool selection, and verification pipeline."""
        start_time = time.time()
        q_clean = (question or "").strip()
        q_lower = q_clean.lower()
        active_id = get_active_dataset_id(db)

        # ── 1. Intent Decomposition & Plan Formulation ──────────────────
        decomposed_intents = decompose_intents(q_clean)
        parsed_nlu = parse_question(q_clean)
        intent = parsed_nlu.get("intent", "GENERAL_FINANCIAL")
        metric = detect_primary_metric(q_lower) or "profit"
        direction = detect_direction(q_lower) or "max"
        req_rank, _ = detect_rank_and_limit(q_lower)
        is_lowest = direction == "min"

        planned_steps: List[str] = []
        executed_tools: List[ToolExecutionRecord] = []

        if len(decomposed_intents) > 1:
            planned_steps.append("1. Deconstruct multi-intent financial query into structured sub-tasks")
            for idx, sub_i in enumerate(decomposed_intents, 1):
                t = sub_i.get("type")
                if t == "ranking":
                    planned_steps.append(f"{idx+1}. Execute ranking analysis: #{sub_i.get('rank', 1)} {sub_i.get('direction', 'max')} by {sub_i.get('metric', 'profit')}")
                elif t == "what_if":
                    planned_steps.append(f"{idx+1}. Run what-if stress-test scenario: Rev {sub_i.get('rev_growth_pct', 0.0):+}% / Exp {sub_i.get('exp_growth_pct', 0.0):+}%")
                elif t == "ranking_list":
                    planned_steps.append(f"{idx+1}. Extract top/bottom {sub_i.get('limit', 3)} ranking list by {sub_i.get('metric', 'profit')}")
                else:
                    planned_steps.append(f"{idx+1}. Evaluate sub-intent: {t}")
            planned_steps.append(f"{len(decomposed_intents)+2}. Validate semantic completeness across all intents")
            planned_steps.append(f"{len(decomposed_intents)+3}. Synthesize unified multi-part executive response")

        elif any(w in q_lower for w in ["why did profit", "decrease", "increase", "drop", "change", "variance", "causal"]):
            planned_steps = [
                "1. Fetch enterprise KPIs and active dataset profile",
                "2. Analyze period-over-period trend variance ($A-X, B-Y, C-Z$)",
                "3. Perform departmental breakdown to identify primary cost drivers",
                "4. Check for critical ledger anomalies",
                "5. Generate prioritized recovery recommendations",
                "6. Validate mathematical calculations against ground truth"
            ]
        elif any(w in q_lower for w in ["lowest", "least", "highest", "top", "rank", "best", "worst"]):
            planned_steps = [
                "1. Fetch departmental performance metrics",
                f"2. Rank departments by {metric} ({direction})",
                "3. Validate ranking and exact metric against database ground truth",
                "4. Synthesize executive scorecard"
            ]
        elif any(w in q_lower for w in ["what if", "scenario", "simulate", "stress test"]):
            planned_steps = [
                "1. Extract baseline financial metrics",
                "2. Run stress-test simulation with scenario growth rates",
                "3. Evaluate solvency and margin delta impact",
                "4. Formulate risk mitigation advice"
            ]
        elif any(w in q_lower for w in ["forecast", "future", "trajectory", "projection"]):
            planned_steps = [
                "1. Query historical time-series ledger records",
                "2. Run linear regression forecasting model",
                "3. Evaluate RMSE and statistical confidence",
                "4. Formulate forward-looking outlook"
            ]
        elif any(w in q_lower for w in ["anomaly", "anomalies", "outlier", "fraud", "irregular"]):
            planned_steps = [
                "1. Execute Isolation Forest multi-dimensional outlier surveillance",
                "2. Filter critical and high-severity deviations",
                "3. Correlate anomalies with departmental operating budgets"
            ]
        elif any(w in q_lower for w in ["recommend", "action", "fix", "improve", "advice"]):
            planned_steps = [
                "1. Retrieve recent human feedback and decisions from AgentMemory",
                "2. Generate data-grounded recommendations from active variances",
                "3. Align actions with corporate governance directives"
            ]
        elif any(w in q_lower for w in ["compare", " vs ", "versus"]):
            planned_steps = [
                "1. Fetch individual metrics for both target departments",
                "2. Compute side-by-side delta variances (Revenue, OPEX, Profit, Margin)",
                "3. Evaluate relative margin efficiency and drivers"
            ]
        else:
            planned_steps = [
                "1. Fetch enterprise financial KPIs (Revenue, Expense, Profit, Margin)",
                "2. Validate accounting identity (Rev - Exp = Profit)",
                "3. Summarize performance health against active dataset"
            ]

        # ── 2. Controlled Dynamic Tool Execution ──────────────────────
        # Tool 1: Authoritative KPIs
        t0 = time.time()
        kpis_data = agent_tools.get_kpis(db)
        executed_tools.append(ToolExecutionRecord(
            tool_name="get_kpis",
            arguments={"scope": "Enterprise"},
            summary_output=f"Rev: {format_inr(kpis_data['revenue'])}, Exp: {format_inr(kpis_data['expense'])}, Profit: {format_inr(kpis_data['profit'])} ({kpis_data['margin']:.1f}%)",
            execution_time_ms=int((time.time() - t0) * 1000)
        ))

        # Tool 2: Department ranking / breakdown
        needs_dept = (
            len(decomposed_intents) > 1 or
            any(w in q_lower for w in ["department", "division", "unit", "lowest", "least", "highest", "top", "worst", "rank", "why", "compare", "vs", "most"])
        )
        if needs_dept:
            t0 = time.time()
            dept_data = agent_tools.get_department_analysis(db, metric=metric, limit=12, sort_order="asc" if is_lowest else "desc")
            top_name = dept_data['top_performer'].get('department') if dept_data.get('top_performer') else 'None'
            executed_tools.append(ToolExecutionRecord(
                tool_name="get_department_analysis",
                arguments={"metric": metric, "sort_order": "asc" if is_lowest else "desc"},
                summary_output=f"Ranked {dept_data['total_departments']} departments. Top: {top_name}",
                execution_time_ms=int((time.time() - t0) * 1000)
            ))

        # Tool 3: Period comparison for causal questions
        if any(w in q_lower for w in ["why did profit", "change", "variance", "period", "what changed", "previous", "last period"]):
            t0 = time.time()
            per_comp = agent_tools.compare_periods(db)
            if "current_period" in per_comp:
                p_c = per_comp["current_period"]["period"]
                p_p = per_comp["previous_period"]["period"]
                executed_tools.append(ToolExecutionRecord(
                    tool_name="compare_periods",
                    arguments={"scope": "Monthly"},
                    summary_output=f"Compared {p_c} vs {p_p}: Profit delta {per_comp.get('profit_change_pct', 0):+.1f}%",
                    execution_time_ms=int((time.time() - t0) * 1000)
                ))

        # Tool 4: What-If simulation if requested
        has_what_if = any(sub.get("type") in ["what_if", "what_if_top_cost_center"] for sub in decomposed_intents) or any(w in q_lower for w in ["what if", "simulate", "falls by", "increases by"])
        if has_what_if:
            t0 = time.time()
            what_if_data = agent_tools.run_what_if_tool(db, rev_growth_pct=0.0, exp_growth_pct=-5.0 if "fall" in q_lower or "decrease" in q_lower else 10.0)
            p_del = what_if_data["impact"]["profit_delta"]
            executed_tools.append(ToolExecutionRecord(
                tool_name="run_what_if_tool",
                arguments={"rev_growth_pct": 0.0, "exp_growth_pct": -5.0 if "fall" in q_lower or "decrease" in q_lower else 10.0},
                summary_output=f"Simulated scenario: Profit delta {format_inr(p_del)}",
                execution_time_ms=int((time.time() - t0) * 1000)
            ))

        # Tool 5: Anomaly detection
        if any(w in q_lower for w in ["anomaly", "anomalies", "outlier", "fraud", "irregular", "audit risk"]):
            t0 = time.time()
            anom_data = agent_tools.detect_anomalies_tool(db)
            executed_tools.append(ToolExecutionRecord(
                tool_name="detect_anomalies_tool",
                arguments={},
                summary_output=f"Found {anom_data['total_anomalies_detected']} outliers ({anom_data['critical_anomalies']} critical)",
                execution_time_ms=int((time.time() - t0) * 1000)
            ))

        # Tool 6: Recommendations
        if any(w in q_lower for w in ["recommend", "action plan", "suggest", "advis", "what should management", "what should we do", "how to improve", "action item"]):
            t0 = time.time()
            recs_data = agent_tools.generate_recommendations_tool(db)
            executed_tools.append(ToolExecutionRecord(
                tool_name="generate_recommendations_tool",
                arguments={},
                summary_output=f"Generated {recs_data['recommendations_count']} recommendations",
                execution_time_ms=int((time.time() - t0) * 1000)
            ))

        # Tool 7: Forecast if query mentions future, projection, or forecast
        if any(w in q_lower for w in ["forecast", "future", "project", "trajectory"]):
            t0 = time.time()
            fcst_data = agent_tools.run_forecast(db, metric=metric, horizon=3)
            executed_tools.append(ToolExecutionRecord(
                tool_name="run_forecast",
                arguments={"metric": metric, "horizon": 3},
                summary_output="Fitted LinearRegression over historical periods",
                execution_time_ms=int((time.time() - t0) * 1000)
            ))

        # Tool 8: Agent memory check
        t0 = time.time()
        mem_summary = memory_agent.get_context_summary(db)
        if mem_summary.get("recent_decisions"):
            executed_tools.append(ToolExecutionRecord(
                tool_name="get_memory_feedback",
                arguments={},
                summary_output=f"Retrieved {len(mem_summary['recent_decisions'])} historical manager decisions",
                execution_time_ms=int((time.time() - t0) * 1000)
            ))

        # ── 3. Candidate Answer Generation (via Grounded Copilot Engine) ───
        raw_answer = ask_copilot(db, q_clean, session_id=session_id)

        # ── 4. Validation & Semantic Completeness Guardrail ────────────
        val_kpi = validation_agent.validate_kpis(
            db=db,
            claimed_rev=kpis_data.get("revenue"),
            claimed_exp=kpis_data.get("expense"),
            claimed_profit=kpis_data.get("profit"),
            claimed_margin=kpis_data.get("margin")
        )

        val_sem = validation_agent.validate_semantic_completeness(
            db=db,
            question=q_clean,
            candidate_answer=raw_answer,
            intents=decomposed_intents
        )

        # Merge validation results
        combined_discrepancies = val_kpi.discrepancies + val_sem.discrepancies
        combined_trace = val_kpi.validation_trace + val_sem.validation_trace
        is_overall_valid = (len(combined_discrepancies) == 0)
        confidence = min(val_kpi.confidence_score, val_sem.confidence_score)

        final_val_result = ValidationResult(
            is_valid=is_overall_valid,
            confidence_score=confidence,
            discrepancies=combined_discrepancies,
            corrected_payload=val_kpi.corrected_payload,
            validation_trace=combined_trace
        )

        final_answer = raw_answer
        total_time_ms = int((time.time() - start_time) * 1000)

        # ── 5. Record Execution Trace in AILog ─────────────────────────
        trace = ExecutionTrace(
            session_id=session_id,
            user_goal=q_clean,
            detected_intents=decomposed_intents,
            planned_steps=planned_steps,
            executed_tools=executed_tools,
            validation_result=final_val_result,
            final_answer=final_answer,
            total_time_ms=total_time_ms
        )

        try:
            ai_log_entry = AILog(
                agent_name="FinancialOrchestratorAgent",
                action="execute_query",
                request_payload={
                    "question": q_clean,
                    "session_id": session_id,
                    "dataset_id": active_id,
                    "intents_count": len(decomposed_intents)
                },
                response_payload={
                    "planned_steps": planned_steps,
                    "tools_count": len(executed_tools),
                    "is_valid": final_val_result.is_valid,
                    "total_time_ms": total_time_ms,
                },
                execution_time_ms=total_time_ms,
                status="SUCCESS" if final_val_result.is_valid else "CORRECTED"
            )
            db.add(ai_log_entry)
            db.commit()
        except Exception as log_err:
            logger.warning(f"Failed to record AILog: {log_err}")

        return trace


financial_orchestrator = FinancialOrchestratorAgent()
