"""
test_agentic_ai.py - Comprehensive Unit & Integration Tests for Agentic AI & Camunda
"""

import pytest
from agents.tools import agent_tools
from agents.validation_agent import validation_agent
from agents.memory_agent import memory_agent
from agents.scenario_agent import scenario_agent
from agents.financial_orchestrator_agent import financial_orchestrator
from services.learning_agent import learning_agent
from camunda.client import camunda_client
from camunda.workers import camunda_worker_service
from services.pl_service import ensure_demo_data
from models.ai_log import AILog


@pytest.fixture(autouse=True)
def seed_demo(db_session):
    ensure_demo_data(db_session, force=True)


def test_agent_tools_kpis(db_session):
    kpis = agent_tools.get_kpis(db_session)
    assert "revenue" in kpis
    assert "expense" in kpis
    assert "profit" in kpis
    assert "margin" in kpis
    assert kpis["revenue"] > 0
    # Identity test: Rev - Exp == Profit
    assert abs((kpis["revenue"] - kpis["expense"]) - kpis["profit"]) < 1.0


def test_agent_tools_department_analysis(db_session):
    dept_analysis = agent_tools.get_department_analysis(db_session, metric="profit", limit=5)
    assert "rankings" in dept_analysis
    assert "total_departments" in dept_analysis
    assert len(dept_analysis["rankings"]) > 0
    assert dept_analysis["top_performer"] is not None


def test_agent_tools_anomalies_and_recommendations(db_session):
    anoms = agent_tools.detect_anomalies_tool(db_session)
    assert "total_anomalies" in anoms or "anomalies" in anoms

    recs = agent_tools.generate_recommendations_tool(db_session)
    assert "recommendations" in recs


def test_agent_tools_forecast_and_what_if(db_session):
    fc = agent_tools.run_forecast(db_session, metric="revenue", horizon=3)
    assert "forecast_result" in fc or "forecasts" in fc

    wi = agent_tools.run_what_if_tool(db_session, rev_growth_pct=10.0, exp_growth_pct=-5.0)
    assert "baseline" in wi
    assert "simulated" in wi
    assert wi["simulated"]["revenue"] > wi["baseline"]["revenue"]


def test_validation_agent_accurate_math(db_session):
    kpis = agent_tools.get_kpis(db_session)
    res = validation_agent.validate_kpis(
        db=db_session,
        claimed_rev=kpis["revenue"],
        claimed_exp=kpis["expense"],
        claimed_profit=kpis["profit"],
        claimed_margin=kpis["margin"]
    )
    assert res.is_valid is True
    assert len(res.discrepancies) == 0
    assert res.confidence_score == 100.0


def test_validation_agent_self_correction(db_session):
    # Pass intentionally hallucinated numbers
    res = validation_agent.validate_kpis(
        db=db_session,
        claimed_rev=999999999.0,
        claimed_exp=1.0,
        claimed_profit=10.0,
        claimed_margin=0.01
    )
    assert res.is_valid is False
    assert len(res.discrepancies) > 0
    assert res.corrected_payload is not None
    assert "revenue" in res.corrected_payload
    assert "profit" in res.corrected_payload


def test_memory_agent_lifecycle(db_session):
    # 1. Record decision
    entry = memory_agent.record_decision(
        db=db_session,
        recommendation_id=42,
        decision="APPROVED",
        notes="Prioritize cloud infrastructure cost containment in Q3."
    )
    assert entry.get("decision") == "APPROVED"

    # 2. Get context summary
    summary = memory_agent.get_context_summary(db_session)
    assert "recent_decisions" in summary
    assert len(summary["recent_decisions"]) >= 1


def test_scenario_agent_stress_test(db_session):
    res = scenario_agent.evaluate_scenario(
        db=db_session,
        rev_growth_pct=-15.0,
        exp_growth_pct=10.0
    )
    assert "calculation" in res or "baseline" in res
    calc = res.get("calculation", res)
    assert "baseline" in calc
    assert "scenario" in calc
    assert "impact" in calc
    assert calc["impact"]["profit_delta"] < 0
    assert "risk_severity" in res


def test_financial_orchestrator_react_loop(db_session):
    # Execute query requiring multi-step investigation
    trace = financial_orchestrator.execute_query(
        db=db_session,
        question="Why did profit change and which department has the lowest margin?",
        session_id="test_react_session",
        user_id=1
    )
    assert trace.user_goal != ""
    assert len(trace.planned_steps) > 0
    assert len(trace.executed_tools) >= 2
    assert trace.final_answer != ""
    assert trace.validation_result is not None

    # Verify AILog entry was written
    ai_logs = db_session.query(AILog).filter(AILog.agent_name == "FinancialOrchestratorAgent").all()
    assert len(ai_logs) > 0


def test_learning_agent_feedback_integration(db_session):
    res = learning_agent.process_recommendation_feedback(
        db=db_session,
        recommendation_id=101,
        decision="APPROVED",
        notes="Approved marketing expansion after CAC analysis."
    )
    assert res["decision_recorded"] == "APPROVED"
    assert res["status"] == "Memory updated"


def test_monitoring_agent_surveillance():
    from services.monitoring_agent import MonitoringAgent
    agent = MonitoringAgent()
    res = agent.analyze_system_health()
    assert res["status"] in ["HEALTHY", "WARNING", "CRITICAL"]
    assert "revenue" in res
    assert "operating_margin" in res
    assert "active_alerts_count" in res


def test_camunda_client_and_workers_lifecycle():
    # Test client fallback when Camunda server is offline
    is_live = camunda_client.is_live()
    assert isinstance(is_live, bool)

    status = camunda_client.get_engine_status()
    assert "engine_url" in status
    assert "is_live" in status

    # Test background worker start/stop
    camunda_worker_service.start()
    assert camunda_worker_service._running is True
    camunda_worker_service.stop()
    assert camunda_worker_service._running is False
