"""
test_copilot_reasoning.py - Comprehensive Test Suite for Hardened Copilot Reasoning
===================================================================================
Tests 29 realistic, compound, comparative, ranking, causal, what-if, and follow-up
financial questions against the live database.
"""

import pytest
import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import SessionLocal
from agents.financial_orchestrator_agent import financial_orchestrator
from services.copilot_agent import ask_copilot, get_financial_context_and_calc
from services.copilot_nlu import decompose_intents, parse_question
from agents.memory_agent import memory_agent


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_q01_most_profitable_department(db_session):
    """Q1: Who is the most profitable department?"""
    q = "Who is the most profitable department?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q1")
    assert "Sales" in trace.final_answer
    assert "₹1.70 Cr" in trace.final_answer or "1,70" in trace.final_answer or "170" in trace.final_answer or "32.1" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q02_second_least_profitable(db_session):
    """Q2: Which department is 2nd least profitable?"""
    q = "Which department is 2nd least profitable?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q2")
    assert "Legal" in trace.final_answer
    assert "2nd" in trace.final_answer or "second" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q03_most_and_second_least_profitable(db_session):
    """Q3: Which department is most profitable and which is 2nd least profitable?"""
    q = "Which department is most profitable and which is 2nd least profitable?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q3")
    assert "Sales" in trace.final_answer
    assert "Legal" in trace.final_answer
    assert len(trace.detected_intents) >= 2
    assert trace.validation_result.is_valid is True


def test_q04_highest_revenue_not_highest_profit(db_session):
    """Q4: Which department has the highest revenue but not the highest profit?"""
    q = "Which department has the highest revenue but not the highest profit?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q4")
    assert "Operations" in trace.final_answer or "Sales" in trace.final_answer
    assert "Revenue" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q05_compare_sales_and_marketing(db_session):
    """Q5: Compare Sales and Marketing."""
    q = "Compare Sales and Marketing."
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q5")
    assert "Sales" in trace.final_answer
    assert "Marketing" in trace.final_answer
    assert "|" in trace.final_answer  # Markdown comparison table
    assert trace.validation_result.is_valid is True


def test_q06_compare_margins_differ(db_session):
    """Q6: Compare Sales and Marketing and tell me why their margins differ."""
    q = "Compare Sales and Marketing and tell me why their margins differ."
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q6")
    assert "Sales" in trace.final_answer
    assert "Marketing" in trace.final_answer
    assert "margin" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q07_why_did_profit_change(db_session):
    """Q7: Why did profit change?"""
    q = "Why did profit change?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q7")
    assert "Period" in trace.final_answer or "Revenue" in trace.final_answer or "Expenses" in trace.final_answer
    assert "Impact" in trace.final_answer or "Variance" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q08_why_did_profit_change_with_top_dept(db_session):
    """Q8: Why did profit change and which department contributed most?"""
    q = "Why did profit change and which department contributed most?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q8")
    assert "Period" in trace.final_answer or "Revenue" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q09_where_are_we_overspending(db_session):
    """Q9: Where are we overspending?"""
    q = "Where are we overspending?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q9")
    assert "Operations" in trace.final_answer or "cost" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q10_what_happens_if_expenses_fall_5_pct(db_session):
    """Q10: What happens if expenses fall 5%?"""
    q = "What happens if expenses fall 5%?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q10")
    assert "Simulation" in trace.final_answer or "Modeled" in trace.final_answer
    assert "Net Profit" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q11_what_if_rev_10_exp_5(db_session):
    """Q11: What happens if revenue increases 10% while expenses increase 5%?"""
    q = "What happens if revenue increases 10% while expenses increase 5%?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q11")
    assert "Simulation" in trace.final_answer or "Scenario" in trace.final_answer
    assert "Net Profit" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q12_lowest_margin_not_lowest_profit(db_session):
    """Q12: Which department has the lowest margin but is not the lowest-profit department?"""
    q = "Which department has the lowest margin but is not the lowest-profit department?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q12")
    assert "Legal" in trace.final_answer or "Human Resources" in trace.final_answer
    assert "margin" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q13_top_3_and_bottom_3_profit(db_session):
    """Q13: Give me the top 3 departments by profit and bottom 3 by profit."""
    q = "Give me the top 3 departments by profit and bottom 3 by profit."
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q13")
    assert "Sales" in trace.final_answer
    assert "Human Resources" in trace.final_answer or "Legal" in trace.final_answer
    assert len(trace.detected_intents) >= 2
    assert trace.validation_result.is_valid is True


def test_q14_highest_expenses_still_profitable(db_session):
    """Q14: Which department has the highest expenses but is still profitable?"""
    q = "Which department has the highest expenses but is still profitable?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q14")
    assert "Operations" in trace.final_answer
    assert "Expenses" in trace.final_answer or "expenditure" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q15_second_most_profitable_and_margin(db_session):
    """Q15: What is the second most profitable department and what is its margin?"""
    q = "What is the second most profitable department and what is its margin?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q15")
    assert "second" in trace.final_answer.lower() or "2nd" in trace.final_answer
    assert "margin" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q16_compare_most_and_least_profitable(db_session):
    """Q16: Compare the most profitable and least profitable departments."""
    q = "Compare the most profitable and least profitable departments."
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q16")
    assert "Sales" in trace.final_answer
    assert "Human Resources" in trace.final_answer
    assert "|" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q17_why_profitable_despite_high_expenses(db_session):
    """Q17: Why is the company profitable despite high expenses?"""
    q = "Why is the company profitable despite high expenses?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q17")
    assert "revenue" in trace.final_answer.lower()
    assert "profit" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q18_largest_expense_increase_dept(db_session):
    """Q18: Which department is responsible for the largest expense increase?"""
    q = "Which department is responsible for the largest expense increase?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q18")
    assert "Operations" in trace.final_answer or "expense" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q19_what_changed_between_latest_two_periods(db_session):
    """Q19: What changed between the latest two periods?"""
    q = "What changed between the latest two periods?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q19")
    assert "Gross Revenue" in trace.final_answer or "Revenue" in trace.final_answer
    assert "Net Profit" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q20_what_changed_in_all_metrics(db_session):
    """Q20: What changed in revenue, expenses, profit and margin?"""
    q = "What changed in revenue, expenses, profit and margin?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q20")
    assert "Revenue" in trace.final_answer
    assert "Expenses" in trace.final_answer
    assert "Profit" in trace.final_answer
    assert "Margin" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q21_what_is_missing_from_dataset(db_session):
    """Q21: What is missing from my dataset?"""
    q = "What is missing from my dataset?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q21")
    assert "Missing" in trace.final_answer or "Schema" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q22_anomalies_affecting_profit(db_session):
    """Q22: Are there anomalies affecting profit?"""
    q = "Are there anomalies affecting profit?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q22")
    assert "anomal" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q23_recommendations_management(db_session):
    """Q23: What recommendations should management consider?"""
    q = "What recommendations should management consider?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q23")
    assert "Management" in trace.final_answer or "recommend" in trace.final_answer.lower()
    assert trace.validation_result.is_valid is True


def test_q24_rejected_recommendations(db_session):
    """Q24: What recommendation was previously rejected?"""
    # Ensure a rejection exists in memory
    memory_agent.record_decision(db_session, 991, "REJECTED", notes="Rejected CapEx expansion due to high interest rates in Q4.")
    q = "What recommendation was previously rejected?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q24")
    assert "REJECTED" in trace.final_answer or "991" in trace.final_answer or "CapEx" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q25_largest_cost_center_reduces_expenses_10_pct(db_session):
    """Q25: What happens if the largest cost center reduces expenses by 10%?"""
    q = "What happens if the largest cost center reduces expenses by 10%?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q25")
    assert "Operations" in trace.final_answer
    assert "Expenses" in trace.final_answer
    assert "Delta" in trace.final_answer or "Improvement" in trace.final_answer or "+" in trace.final_answer
    assert trace.validation_result.is_valid is True


def test_q26_follow_up_why(db_session):
    """Q26: Conversational follow-up 'Why?' after asking least profitable."""
    session_id = "test_conv_flow_1"
    # Step 1: Ask least profitable
    t1 = financial_orchestrator.execute_query(db_session, "Which department is least profitable?", session_id=session_id)
    assert "Human Resources" in t1.final_answer

    # Step 2: Ask Why?
    t2 = financial_orchestrator.execute_query(db_session, "Why?", session_id=session_id)
    assert "Human Resources" in t2.final_answer
    assert "revenue" in t2.final_answer.lower()
    assert "expense" in t2.final_answer.lower()


def test_q27_follow_up_what_about_legal(db_session):
    """Q27: Conversational follow-up 'What about Legal?'"""
    session_id = "test_conv_flow_2"
    # Step 1: Ask least profitable (Human Resources)
    t1 = financial_orchestrator.execute_query(db_session, "Which department is least profitable?", session_id=session_id)
    assert "Human Resources" in t1.final_answer

    # Step 2: Ask What about Legal?
    t2 = financial_orchestrator.execute_query(db_session, "What about Legal?", session_id=session_id)
    assert "Legal" in t2.final_answer
    assert "Human Resources" in t2.final_answer  # Side-by-side comparison with previous context


def test_q28_three_part_multi_intent(db_session):
    """Q28: Three-part multi-intent query."""
    q = "Which department is most profitable, which is least profitable, and what happens if expenses fall 5%?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q28")
    assert "Sales" in trace.final_answer
    assert "Human Resources" in trace.final_answer
    assert "Simulation" in trace.final_answer or "Net Profit" in trace.final_answer
    assert len(trace.detected_intents) >= 3
    assert trace.validation_result.is_valid is True


def test_q29_out_of_scope_query(db_session):
    """Q29: Out of scope non-financial question."""
    q = "What is Apple stock price today?"
    trace = financial_orchestrator.execute_query(db_session, q, session_id="test_q29")
    assert "outside the scope" in trace.final_answer.lower() or "cannot determine" in trace.final_answer.lower()
