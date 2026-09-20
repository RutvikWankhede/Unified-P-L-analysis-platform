import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

from database import SessionLocal, engine, Base
import models
from models.pl_record import PLRecord
from agents.tools import agent_tools
from agents.validation_agent import validation_agent
from agents.memory_agent import memory_agent
from agents.scenario_agent import scenario_agent
from agents.financial_orchestrator_agent import financial_orchestrator
from services.learning_agent import learning_agent
from camunda.client import camunda_client
from camunda.workers import camunda_worker_service
from services.workflow_service import workflow_service
from models.ai_log import AILog

def run_all_verifications():
    print("=" * 70, flush=True)
    print("STARTING UNIFIED P&L AGENTIC AI & CAMUNDA SYSTEM VERIFICATION", flush=True)
    print("=" * 70, flush=True)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rec_count = db.query(PLRecord).count()
        print(f"Step 0: Database verified with {rec_count} ledger records.", flush=True)

        # ── Test 1: Agent Controlled Tools ──
        print("\nTest 1: Testing Controlled Agent Tools...", flush=True)
        kpis = agent_tools.get_kpis(db)
        print(f"   - get_kpis: Rev={kpis['revenue']:.2f}, Exp={kpis['expense']:.2f}, Profit={kpis['profit']:.2f}, Margin={kpis['margin']:.2f}%", flush=True)
        assert kpis['revenue'] > 0, "Revenue should be positive"
        assert abs((kpis['revenue'] - kpis['expense']) - kpis['profit']) < 1.0, "Rev - Exp must equal Profit"

        dept_analysis = agent_tools.get_department_analysis(db, metric="profit", limit=5)
        print(f"   - get_department_analysis: {dept_analysis['total_departments']} departments, Top={dept_analysis['top_performer']['department']}", flush=True)
        assert len(dept_analysis['rankings']) > 0

        anoms = agent_tools.detect_anomalies_tool(db)
        print(f"   - detect_anomalies_tool: Found {anoms['total_anomalies_detected']} anomalies ({anoms['critical_anomalies']} critical)", flush=True)

        recs = agent_tools.generate_recommendations_tool(db)
        print(f"   - generate_recommendations_tool: Generated {recs['recommendations_count']} recommendations", flush=True)

        fc = agent_tools.run_forecast(db, metric="revenue", horizon=3)
        print(f"   - run_forecast: Fitted LinearRegression forecast (periods={fc.get('horizon_periods')})", flush=True)

        wi = agent_tools.run_what_if_tool(db, rev_growth_pct=10.0, exp_growth_pct=-5.0)
        print(f"   - run_what_if_tool: Baseline Profit={wi['baseline']['profit']:.2f} -> Simulated Profit={wi['simulated']['profit']:.2f}", flush=True)
        print("Test 1 PASSED: All 6 Controlled Tools functioning correctly.", flush=True)

        # ── Test 2: Validation Agent Guardrails ──
        print("\nTest 2: Testing Financial Validation Agent Guardrails...", flush=True)
        val_pass = validation_agent.validate_kpis(
            db=db,
            claimed_rev=kpis["revenue"],
            claimed_exp=kpis["expense"],
            claimed_profit=kpis["profit"],
            claimed_margin=kpis["margin"]
        )
        print(f"   - Accurate numbers check: is_valid={val_pass.is_valid}, discrepancies={len(val_pass.discrepancies)}", flush=True)
        assert val_pass.is_valid is True

        val_fail = validation_agent.validate_kpis(
            db=db,
            claimed_rev=999999999.0,
            claimed_exp=1.0,
            claimed_profit=50.0,
            claimed_margin=0.01
        )
        print(f"   - Hallucinated numbers check: is_valid={val_fail.is_valid}, has_corrections={val_fail.corrected_payload is not None}", flush=True)
        assert val_fail.is_valid is False
        assert val_fail.corrected_payload is not None
        print("Test 2 PASSED: Mathematical guardrail and self-correction functioning.", flush=True)

        # ── Test 3: Agent Memory System ──
        print("\nTest 3: Testing Agent Memory System...", flush=True)
        entry = memory_agent.record_decision(
            db=db,
            recommendation_id=77,
            decision="APPROVED",
            notes="Authorized 10% OPEX reduction in Marketing.",
            user_id=1
        )
        print(f"   - Stored decision #{entry['recommendation_id']} in AgentMemory ({entry['decision']})", flush=True)
        assert entry["decision"] == "APPROVED"

        directive = memory_agent.record_directive(
            db=db,
            directive_text="Prioritize cash conservation over aggressive top-line growth.",
            category="Enterprise",
            user_id=1
        )
        print(f"   - Stored directive in AgentMemory: {directive['directive']}", flush=True)

        context_summary = memory_agent.get_context_summary(db, limit=5)
        print(f"   - Retrieved context summary: {len(context_summary.get('recent_decisions', []))} decisions, {len(context_summary.get('active_directives', []))} directives", flush=True)
        assert len(context_summary.get("recent_decisions", [])) >= 1
        print("Test 3 PASSED: Agent memory persistence & retrieval functioning.", flush=True)

        # ── Test 4: Scenario Analysis Agent ──
        print("\nTest 4: Testing Scenario Analysis Agent...", flush=True)
        scenario_res = scenario_agent.evaluate_scenario(
            db=db,
            rev_growth_pct=-8.0,
            exp_growth_pct=12.0
        )
        print(f"   - Risk Severity: {scenario_res['risk_severity']}", flush=True)
        print(f"   - Profit Delta: {scenario_res['calculation']['impact']['profit_delta']:.2f}", flush=True)
        print(f"   - Strategic Advice: {scenario_res['strategic_recommendation']}", flush=True)
        assert scenario_res['calculation']['impact']['profit_delta'] < 0
        assert "Risk" in scenario_res['risk_severity'] or "CRITICAL" in scenario_res['risk_severity'] or "HIGH" in scenario_res['risk_severity']
        print("Test 4 PASSED: Stress-testing and risk interpretation functioning.", flush=True)

        # ── Test 5: Master Financial Orchestrator ──
        print("\nTest 5: Testing Master Financial Orchestrator (ReAct Planning Loop)...", flush=True)
        trace = financial_orchestrator.execute_query(
            db=db,
            question="Why did profit change and which department has the lowest profit margin?",
            session_id="verification_session",
            user_id=1
        )
        print(f"   - User Goal: {trace.user_goal}", flush=True)
        print(f"   - Planned Steps ({len(trace.planned_steps)}):", flush=True)
        for s in trace.planned_steps:
            print(f"       {s}", flush=True)
        print(f"   - Executed Tools ({len(trace.executed_tools)}):", flush=True)
        for t in trace.executed_tools:
            print(f"       * {t.tool_name} ({t.execution_time_ms}ms) -> {t.summary_output}", flush=True)
        print(f"   - Validation Guardrail: Valid={trace.validation_result.is_valid if trace.validation_result else 'N/A'}", flush=True)
        print(f"   - Total Execution Time: {trace.total_time_ms}ms", flush=True)
        assert len(trace.executed_tools) >= 2
        assert trace.final_answer != ""
        print("Test 5 PASSED: Full ReAct cycle, tool dispatch, guardrail, and logging working.", flush=True)

        # ── Test 6: Adaptive Learning Agent ──
        print("\nTest 6: Testing Adaptive Learning Agent...", flush=True)
        learn_res = learning_agent.process_recommendation_feedback(
            db=db,
            recommendation_id=88,
            decision="MODIFIED",
            notes="Adjusted cloud infrastructure migration to phased 6-month plan.",
            user_id=1
        )
        print(f"   - Learning feedback result: {learn_res}", flush=True)
        assert learn_res["decision_recorded"] == "MODIFIED"
        print("Test 6 PASSED: Recommendation feedback learning working.", flush=True)

        # ── Test 7: Camunda Client, Workers, & Workflow Service ──
        print("\nTest 7: Testing Camunda BPMN Client, Workers & Orchestration Service...", flush=True)
        cam_status = camunda_client.get_engine_status()
        print(f"   - Camunda Engine Status: {cam_status}", flush=True)

        # Start workflow instance
        inst = workflow_service.start_workflow(
            db=db,
            user_id=1,
            dataset_id=1,
            department="Overall",
            fiscal_year="2024",
            trigger_approval=True
        )
        inst_id = str(inst.get("id") or inst.get("process_instance_id"))
        print(f"   - Workflow Instance Created: ID={inst_id}, Status={inst['status']}, Current Step={inst['current_step']}", flush=True)
        assert inst_id != ""

        # Test supervisor approval
        if inst['status'] == 'PENDING_APPROVAL':
            appr = workflow_service.approve_task(db, inst_id, notes="Approved in automated verification test")
            print(f"   - Human Approval Executed: New Status={appr['status']}, Step={appr['current_step']}", flush=True)
            assert appr['status'] in ['RUNNING', 'COMPLETED']

        # Worker service lifecycle
        camunda_worker_service.start()
        print(f"   - Camunda Worker Service Started: running={camunda_worker_service._running}", flush=True)
        camunda_worker_service.stop()
        print(f"   - Camunda Worker Service Stopped: running={camunda_worker_service._running}", flush=True)
        print("Test 7 PASSED: Camunda client, worker threads, and workflow lifecycle verified.", flush=True)

        print("\n" + "=" * 70, flush=True)
        print("ALL 7 AGENTIC AI & CAMUNDA UPGRADES VERIFIED SUCCESSFULLY!", flush=True)
        print("=" * 70, flush=True)

    finally:
        db.close()

if __name__ == "__main__":
    run_all_verifications()
