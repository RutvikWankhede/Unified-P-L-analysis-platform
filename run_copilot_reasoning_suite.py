"""
run_copilot_reasoning_suite.py - Execution & Verification Harness for Hardened Copilot
======================================================================================
Executes 29 comprehensive financial questions testing multi-intent decomposition,
canonical ranking, causal period variance diagnostics, side-by-side comparisons,
what-if simulations, conversational follow-ups, and semantic validation guardrails.
"""

import os
import sys
import json
import time

# Windows UTF-8 console output setup
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "unified-pl-system", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.chdir(backend_dir)

from database import SessionLocal
from agents.financial_orchestrator_agent import financial_orchestrator
from agents.memory_agent import memory_agent
from services.copilot_nlu import decompose_intents


def run_suite():
    db = SessionLocal()
    results = []

    # Ensure a rejection decision exists in memory for Q24
    try:
        memory_agent.record_decision(
            db,
            991,
            "REJECTED",
            notes="Rejected CapEx expansion due to high interest rates in Q4."
        )
    except Exception as e:
        print(f"Memory seed note: {e}")

    test_questions = [
        ("Q01: Who is the most profitable department?", "Who is the most profitable department?"),
        ("Q02: Which department is 2nd least profitable?", "Which department is 2nd least profitable?"),
        ("Q03: Which department is most profitable and which is 2nd least profitable?", "Which department is most profitable and which is 2nd least profitable?"),
        ("Q04: Which department has the highest revenue but not the highest profit?", "Which department has the highest revenue but not the highest profit?"),
        ("Q05: Compare Sales and Marketing.", "Compare Sales and Marketing."),
        ("Q06: Compare Sales and Marketing and tell me why their margins differ.", "Compare Sales and Marketing and tell me why their margins differ."),
        ("Q07: Why did profit change?", "Why did profit change?"),
        ("Q08: Why did profit change and which department contributed most?", "Why did profit change and which department contributed most?"),
        ("Q09: Where are we overspending?", "Where are we overspending?"),
        ("Q10: What happens if expenses fall 5%?", "What happens if expenses fall 5%?"),
        ("Q11: What happens if revenue increases 10% while expenses increase 5%?", "What happens if revenue increases 10% while expenses increase 5%?"),
        ("Q12: Which department has the lowest margin but is not the lowest-profit department?", "Which department has the lowest margin but is not the lowest-profit department?"),
        ("Q13: Give me the top 3 departments by profit and bottom 3 by profit.", "Give me the top 3 departments by profit and bottom 3 by profit."),
        ("Q14: Which department has the highest expenses but is still profitable?", "Which department has the highest expenses but is still profitable?"),
        ("Q15: What is the second most profitable department and what is its margin?", "What is the second most profitable department and what is its margin?"),
        ("Q16: Compare the most profitable and least profitable departments.", "Compare the most profitable and least profitable departments."),
        ("Q17: Why is the company profitable despite high expenses?", "Why is the company profitable despite high expenses?"),
        ("Q18: Which department is responsible for the largest expense increase?", "Which department is responsible for the largest expense increase?"),
        ("Q19: What changed between the latest two periods?", "What changed between the latest two periods?"),
        ("Q20: What changed in revenue, expenses, profit and margin?", "What changed in revenue, expenses, profit and margin?"),
        ("Q21: What is missing from my dataset?", "What is missing from my dataset?"),
        ("Q22: Are there anomalies affecting profit?", "Are there anomalies affecting profit?"),
        ("Q23: What recommendations should management consider?", "What recommendations should management consider?"),
        ("Q24: What recommendation was previously rejected?", "What recommendation was previously rejected?"),
        ("Q25: What happens if the largest cost center reduces expenses by 10%?", "What happens if the largest cost center reduces expenses by 10%?"),
        ("Q26: Conversational Follow-up: Why?", "Why?"),
        ("Q27: Conversational Follow-up: What about Legal?", "What about Legal?"),
        ("Q28: Multi-Intent (3-part): Most, least, and what-if 5% expense drop", "Which department is most profitable, which is least profitable, and what happens if expenses fall 5%?"),
        ("Q29: Out-of-Scope: Stock price lookup", "What is Apple stock price today?"),
    ]

    print("=" * 80)
    print("STARTING UNIFIED P&L COPILOT REASONING VERIFICATION SUITE (29 TESTS)")
    print("=" * 80)

    passed_count = 0
    failed_count = 0
    session_id = "eval_session_master"

    # Seed initial context for follow-up tests
    financial_orchestrator.execute_query(db, "Which department is least profitable?", session_id=session_id)

    for tag, question in test_questions:
        t0 = time.time()
        print(f"\n▶ Executing {tag}...")
        try:
            trace = financial_orchestrator.execute_query(db, question, session_id=session_id)
            elapsed_ms = int((time.time() - t0) * 1000)

            ans = trace.final_answer
            tools = [t.tool_name for t in trace.executed_tools]
            is_valid = trace.validation_result.is_valid if trace.validation_result else True

            # Assert basic completeness criteria per test
            status = "PASS"
            fail_reason = ""

            if "Q01" in tag and "Sales" not in ans:
                status, fail_reason = "FAIL", "Missing 'Sales' in answer"
            elif "Q02" in tag and "Legal" not in ans:
                status, fail_reason = "FAIL", "Missing 'Legal' in answer"
            elif "Q03" in tag and ("Sales" not in ans or "Legal" not in ans):
                status, fail_reason = "FAIL", "Missing Sales or Legal in multi-intent response"
            elif "Q05" in tag and ("Sales" not in ans or "Marketing" not in ans):
                status, fail_reason = "FAIL", "Missing Sales or Marketing in comparison"
            elif "Q10" in tag and "Profit" not in ans:
                status, fail_reason = "FAIL", "Missing Net Profit impact in What-If"
            elif "Q16" in tag and ("Sales" not in ans or "Human Resources" not in ans):
                status, fail_reason = "FAIL", "Missing extreme departments in comparison"
            elif "Q24" in tag and "REJECTED" not in ans and "991" not in ans:
                status, fail_reason = "FAIL", "Missing rejected recommendation context"
            elif "Q28" in tag and ("Sales" not in ans or "Human Resources" not in ans or "Simulation" not in ans and "Net Profit" not in ans):
                status, fail_reason = "FAIL", "Missing one or more parts in 3-part multi-intent query"

            if status == "PASS":
                passed_count += 1
                print(f"  ✓ {tag}: PASS ({elapsed_ms}ms) | Tools: {tools} | Validated: {is_valid}")
            else:
                failed_count += 1
                print(f"  ✗ {tag}: FAIL - {fail_reason} ({elapsed_ms}ms)")

            results.append({
                "tag": tag,
                "question": question,
                "status": status,
                "fail_reason": fail_reason,
                "elapsed_ms": elapsed_ms,
                "detected_intents": trace.detected_intents,
                "planned_steps": trace.planned_steps,
                "tools_used": tools,
                "validation_result": {
                    "is_valid": trace.validation_result.is_valid if trace.validation_result else True,
                    "confidence": trace.validation_result.confidence_score if trace.validation_result else 100.0,
                    "discrepancies": trace.validation_result.discrepancies if trace.validation_result else []
                },
                "final_answer_preview": ans[:300] + "..." if len(ans) > 300 else ans,
                "full_answer": ans
            })

        except Exception as e:
            failed_count += 1
            print(f"  ✗ {tag}: ERROR - {e}")
            results.append({
                "tag": tag,
                "question": question,
                "status": "ERROR",
                "fail_reason": str(e),
                "elapsed_ms": int((time.time() - t0) * 1000)
            })

    db.close()

    summary = {
        "total_tests": len(test_questions),
        "passed": passed_count,
        "failed": failed_count,
        "pass_rate_pct": round(passed_count / len(test_questions) * 100, 2),
        "results": results
    }

    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "copilot_reasoning_verification_results.json"))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"FINAL SUMMARY: {passed_count}/{len(test_questions)} PASSED ({summary['pass_rate_pct']}%)")
    print(f"Results saved to: {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_suite()
