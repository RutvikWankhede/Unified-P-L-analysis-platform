"""
scenario_agent.py - What-If Scenario Analysis Agent
====================================================
Provides strategic reasoning, risk evaluation, and mitigation advice
grounded in the deterministic What-If simulation engine.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.tools import agent_tools
from services.copilot_agent import format_inr, format_margin

logger = logging.getLogger(__name__)


class WhatIfScenarioAgent:
    """Agent that stress-tests financials and formulates strategic risk interpretations."""

    def evaluate_scenario(
        self,
        db: Session,
        rev_growth_pct: float = 0.0,
        exp_growth_pct: float = 0.0,
        dept: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluates stress-test impact and produces a structured strategic briefing."""
        calc = agent_tools.run_what_if_tool(
            db=db,
            rev_growth_pct=rev_growth_pct,
            exp_growth_pct=exp_growth_pct,
            dept=dept
        )

        base = calc["baseline"]
        scen = calc["scenario"]
        imp = calc["impact"]

        prof_delta = imp["profit_delta"]
        is_pos = prof_delta >= 0

        # Risk severity classification
        if scen["profit"] < 0:
            risk_severity = "CRITICAL (Operating Deficit Triggered)"
            recommendation = "Enforce emergency spending freezes across non-revenue generating units."
        elif imp["margin_delta_pct"] < -5.0:
            risk_severity = "HIGH (Severe Margin Dilution)"
            recommendation = "Re-evaluate procurement terms and variable overheads to protect operating profitability."
        elif imp["margin_delta_pct"] < 0.0:
            risk_severity = "MODERATE (Mild Margin Squeeze)"
            recommendation = "Monitor quarterly OPEX trajectories and optimize discretionary departmental budgets."
        else:
            risk_severity = "LOW (Accretive Performance Expansion)"
            recommendation = "Maintain operational momentum and allocate surplus operating cash toward high-margin commercial expansion."

        narrative = (
            f"### What-If Stress-Test Assessment\n\n"
            f"Under a **{rev_growth_pct:+.1f}% Revenue** and **{exp_growth_pct:+.1f}% Expense** adjustment:\n\n"
            f"- **Projected Net Profit:** **{format_inr(scen['profit'])}** (Delta: {format_inr(prof_delta)} vs baseline {format_inr(base['profit'])})\n"
            f"- **Projected Operating Margin:** **{format_margin(scen['margin'])}** (Shift: {imp['margin_delta_pct']:+.2f}% pts)\n"
            f"- **Projected Gross Revenue:** {format_inr(scen['revenue'])}\n"
            f"- **Projected Expenditures:** {format_inr(scen['expense'])}\n\n"
            f"**Risk Severity:** `{risk_severity}`\n\n"
            f"**Strategic Recommendation:** {recommendation}\n\n"
            f"*Source: Active dataset simulation calculations*"
        )

        return {
            "calculation": calc,
            "risk_severity": risk_severity,
            "strategic_recommendation": recommendation,
            "narrative": narrative,
        }


scenario_agent = WhatIfScenarioAgent()
