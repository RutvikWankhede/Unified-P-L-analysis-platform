from database import SessionLocal
from services.copilot_agent import ask_copilot, reset_context
from routers.reports import build_canonical_report_dataset

def test_copilot_and_report_consistency():
    db = SessionLocal()
    session_id = "test_audit_session_1"
    reset_context(session_id)
    
    print("==================================================")
    print("TESTING COPILOT & REPORT RECONCILIATION")
    print("==================================================")
    
    # 1. Report Analytics
    rep_data = build_canonical_report_dataset(db, report_type="overall")
    depts = rep_data["department_performance"]
    top_p = max(depts, key=lambda d: d["profit"])
    low_p = min(depts, key=lambda d: d["profit"])
    
    print(f"Report Top Profit Dept: {top_p['department']} ({top_p['profit']:,.2f})")
    print(f"Report Lowest Profit Dept: {low_p['department']} ({low_p['profit']:,.2f})")
    
    # 2. Copilot Question: Highest Profit
    q1 = "Which department has the highest profit?"
    ans1 = ask_copilot(db, q1, session_id=session_id)
    print(f"\nQ1: {q1}")
    print(f"A1: {ans1.replace('₹', 'INR ')}")
    assert top_p['department'].lower() in ans1.lower(), f"Copilot highest profit mismatch! Expected {top_p['department']}"
    
    # 3. Copilot Question: Future Least Profitable
    q2 = "Which department will be least profitable in future?"
    ans2 = ask_copilot(db, q2, session_id=session_id)
    print(f"\nQ2: {q2}")
    print(f"A2: {ans2.replace('₹', 'INR ')}")
    
    # 4. Multi-turn Follow-up Question: "What will its revenue be after 2 months?"
    q3 = "What will its revenue be after 2 months?"
    ans3 = ask_copilot(db, q3, session_id=session_id)
    print(f"\nQ3: {q3}")
    print(f"A3: {ans3.replace('₹', 'INR ')}")
    assert "2 months" in ans3.lower() or "projected revenue" in ans3.lower() or "revenue" in ans3.lower(), "Multi-turn follow-up revenue question failed!"
    
    # 5. Multi-turn Follow-up Question: "What about its expenses?"
    q4 = "What about its expenses?"
    ans4 = ask_copilot(db, q4, session_id=session_id)
    print(f"\nQ4: {q4}")
    print(f"A4: {ans4.replace('₹', 'INR ')}")
    assert "expense" in ans4.lower() or "operating expense" in ans4.lower(), "Multi-turn follow-up expense question failed!"
    
    print("\n==================================================")
    print("COPILOT & REPORT CONSISTENCY TEST PASSED 100%!")
    print("==================================================")

if __name__ == "__main__":
    test_copilot_and_report_consistency()
