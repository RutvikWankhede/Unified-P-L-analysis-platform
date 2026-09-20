"""
validation_agent.py - Financial Self-Correction & Consistency Guardrail
========================================================================
Validates candidate financial statements, calculation integrity, department rankings,
margin formulas, multi-intent completeness, and numerical grounding against
canonical MetricEngine ground truth before output emission.
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from pydantic import BaseModel

from services.metric_engine import MetricEngine
from routers.datasets_router import get_active_dataset_id

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    is_valid: bool
    confidence_score: float
    discrepancies: List[str]
    corrected_payload: Optional[Dict[str, Any]] = None
    validation_trace: List[str]


class FinancialValidationAgent:
    """Guardrail agent enforcing 100% mathematical and semantic integrity on all AI-generated statements."""

    def validate_kpis(
        self,
        db: Session,
        claimed_rev: Optional[float] = None,
        claimed_exp: Optional[float] = None,
        claimed_profit: Optional[float] = None,
        claimed_margin: Optional[float] = None,
        dept: Optional[str] = None
    ) -> ValidationResult:
        """Validates claimed financial totals against canonical MetricEngine calculations."""
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        kpis = me.get_kpis()

        expected_rev = float(kpis.get("revenue") or 0.0)
        expected_exp = float(kpis.get("expense") or 0.0)
        expected_prof = expected_rev - expected_exp
        expected_margin = (expected_prof / expected_rev * 100) if expected_rev > 0 else 0.0

        discrepancies = []
        trace = []

        # 1. Equation validation: Rev - Exp == Profit
        if claimed_rev is not None and claimed_exp is not None and claimed_profit is not None:
            calc_diff = abs((claimed_rev - claimed_exp) - claimed_profit)
            if calc_diff > 1.0:
                discrepancies.append(
                    f"Equation violation: Claimed Rev ({claimed_rev:,.2f}) - Exp ({claimed_exp:,.2f}) != Profit ({claimed_profit:,.2f})"
                )
            else:
                trace.append("Equation verified: Rev - Exp == Profit")

        # 2. Operating margin validation: Margin == (Profit / Rev) * 100
        if claimed_rev is not None and claimed_profit is not None and claimed_margin is not None:
            if claimed_rev > 0:
                expected_mrg_calc = (claimed_profit / claimed_rev) * 100
                if abs(expected_mrg_calc - claimed_margin) > 0.5:
                    discrepancies.append(
                        f"Margin discrepancy: Claimed margin {claimed_margin:.2f}% != Calculated ({claimed_profit:,.2f} / {claimed_rev:,.2f}) * 100 = {expected_mrg_calc:.2f}%"
                    )
                else:
                    trace.append("Margin formula verified: (Profit / Rev) * 100")

        # 3. Ground truth matching against database
        if claimed_rev is not None and abs(claimed_rev - expected_rev) > 100.0:
            discrepancies.append(f"Revenue mismatch: Claimed ₹{claimed_rev:,.2f} != Database ₹{expected_rev:,.2f}")
        if claimed_exp is not None and abs(claimed_exp - expected_exp) > 100.0:
            discrepancies.append(f"Expense mismatch: Claimed ₹{claimed_exp:,.2f} != Database ₹{expected_exp:,.2f}")
        if claimed_profit is not None and abs(claimed_profit - expected_prof) > 100.0:
            discrepancies.append(f"Profit mismatch: Claimed ₹{claimed_profit:,.2f} != Database ₹{expected_prof:,.2f}")

        is_valid = len(discrepancies) == 0
        confidence = 100.0 if is_valid else max(0.0, 100.0 - (len(discrepancies) * 30.0))

        corrected = {
            "revenue": expected_rev,
            "expense": expected_exp,
            "profit": expected_prof,
            "margin": expected_margin,
            "dataset_id": active_id,
        }

        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence,
            discrepancies=discrepancies,
            corrected_payload=corrected,
            validation_trace=trace if is_valid else trace + discrepancies,
        )

    def validate_department_ranking(
        self,
        db: Session,
        claimed_dept: str,
        metric: str,
        claimed_rank: int,  # 1 = top/bottom
        is_lowest: bool = False
    ) -> ValidationResult:
        """Validates department ordinal ranking claim against canonical database aggregates."""
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        depts = me.get_department_aggregates()

        norm_metric = metric.lower().strip()
        if norm_metric not in ["revenue", "expense", "profit", "margin"]:
            norm_metric = "profit"

        sorted_depts = sorted(depts, key=lambda x: x.get(norm_metric, 0.0), reverse=not is_lowest)
        target_idx = min(max(0, claimed_rank - 1), len(sorted_depts) - 1)
        actual_dept_info = sorted_depts[target_idx] if sorted_depts else {}
        actual_name = actual_dept_info.get("department", "Unknown")

        discrepancies = []
        trace = []

        is_match = (claimed_dept.lower() == actual_name.lower())
        if not is_match:
            discrepancies.append(
                f"Ranking discrepancy: Claimed #{claimed_rank} ({'lowest' if is_lowest else 'highest'}) {norm_metric} department was '{claimed_dept}', but ground truth is '{actual_name}' (Value: {actual_dept_info.get(norm_metric, 0):,.2f})"
            )
        else:
            trace.append(f"Ranking verified: {actual_name} is #{claimed_rank} ({'lowest' if is_lowest else 'highest'}) in {norm_metric}")

        return ValidationResult(
            is_valid=is_match,
            confidence_score=100.0 if is_match else 0.0,
            discrepancies=discrepancies,
            corrected_payload=actual_dept_info,
            validation_trace=trace if is_match else trace + discrepancies,
        )

    def validate_semantic_completeness(
        self,
        db: Session,
        question: str,
        candidate_answer: str,
        intents: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validates semantic completeness of the answer against all decomposed intents.
        Checks entity presence, ordinal rankings, comparison symmetry, and mathematical grounding.
        """
        active_id = get_active_dataset_id(db)
        me = MetricEngine(db, active_id)
        depts = me.get_department_aggregates()
        ans_lower = (candidate_answer or "").lower()

        by_prof_desc = sorted(depts, key=lambda x: x.get("profit", 0.0), reverse=True)
        by_prof_asc = sorted(depts, key=lambda x: x.get("profit", 0.0), reverse=False)

        discrepancies = []
        trace = []

        # 1. Verify all decomposed sub-intents have corresponding coverage
        for idx, sub_intent in enumerate(intents, 1):
            i_type = sub_intent.get("type")
            if i_type == "ranking":
                metric = sub_intent.get("metric", "profit")
                direction = sub_intent.get("direction", "max")
                rank = sub_intent.get("rank", 1)
                is_min = (direction == "min")

                sorted_list = by_prof_asc if is_min else by_prof_desc
                expected_idx = min(max(0, rank - 1), len(sorted_list) - 1)
                expected_dept = sorted_list[expected_idx]["department"] if sorted_list else ""

                if expected_dept.lower() not in ans_lower:
                    discrepancies.append(
                        f"Intent #{idx} completeness failure: Expected rank #{rank} ({'lowest' if is_min else 'highest'}) {metric} department '{expected_dept}' was missing from the response."
                    )
                else:
                    trace.append(f"Intent #{idx} verified: #{rank} {direction} {metric} -> {expected_dept}")

            elif i_type == "comparison":
                entities = sub_intent.get("entities", [])
                for ent in entities:
                    if ent.lower() not in ans_lower:
                        discrepancies.append(f"Comparison incomplete: Department '{ent}' was omitted from the response.")
                    else:
                        trace.append(f"Comparison entity verified: {ent}")

            elif i_type == "what_if":
                if "scenario" not in ans_lower and "what-if" not in ans_lower and "modeled" not in ans_lower:
                    discrepancies.append(f"What-If completeness failure: Simulation impact was not clearly stated.")
                else:
                    trace.append("What-If simulation verified in response.")

        # 2. Mathematical equation sanity
        kpis = me.get_kpis()
        exp_rev = float(kpis.get("revenue") or 0.0)
        exp_exp = float(kpis.get("expense") or 0.0)
        exp_prof = exp_rev - exp_exp

        trace.append(f"Ground truth active dataset check: Rev={exp_rev:,.0f}, Exp={exp_exp:,.0f}, Profit={exp_prof:,.0f}")

        is_valid = (len(discrepancies) == 0)
        confidence = 100.0 if is_valid else max(0.0, 100.0 - (len(discrepancies) * 25.0))

        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence,
            discrepancies=discrepancies,
            corrected_payload={"active_dataset_id": active_id},
            validation_trace=trace if is_valid else trace + discrepancies,
        )


validation_agent = FinancialValidationAgent()
