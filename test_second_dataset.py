import os
import io
import sys
import pandas as pd
import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"

def run_test():
    # 1. Login
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[1] Logged in as admin", flush=True)

    # 2. Generate a custom CSV with non-standard column names
    # Using columns: Transaction Date, Dept, Sales, Cost, Gain
    data = []
    dates = ["2024-01-15", "2024-02-15", "2024-03-15", "2024-04-15", "2024-05-15", "2024-06-15"]
    depts = ["Commercial", "Technology", "Logistics"]
    
    for d in dates:
        for dept in depts:
            sales = 500000.0 if dept == "Commercial" else (300000.0 if dept == "Technology" else 200000.0)
            cost = 250000.0 if dept == "Commercial" else (180000.0 if dept == "Technology" else 150000.0)
            gain = sales - cost
            data.append({
                "Transaction Date": d,
                "Dept": dept,
                "Sales": sales,
                "Cost": cost,
                "Gain": gain
            })
            
    df_new = pd.DataFrame(data)
    csv_bytes = df_new.to_csv(index=False).encode("utf-8")
    
    # 3. Upload the new dataset
    files = {"file": ("q1_q2_secondary_dataset.csv", csv_bytes, "text/csv")}
    up_res = requests.post(f"{BASE_URL}/api/v1/pl/upload", files=files, headers=headers)
    assert up_res.status_code == 201, f"Upload failed: {up_res.text}"
    up_json = up_res.json()
    upload_id = up_json["upload_id"]
    analysis = up_json["analysis"]
    print(f"[2] Secondary dataset uploaded successfully! Upload ID: {upload_id}", flush=True)
    print(f"    Suggested Mapping: {analysis['suggested_mapping']}", flush=True)

    # 4. Finalize ingestion
    finalize_payload = {
        "upload_id": upload_id,
        "filename": "q1_q2_secondary_dataset.csv",
        "mapping": analysis["suggested_mapping"]
    }
    fin_res = requests.post(f"{BASE_URL}/api/v1/pl/finalize-upload", json=finalize_payload, headers=headers)
    assert fin_res.status_code == 201, f"Finalize failed: {fin_res.text}"
    print(f"[3] Finalized ingestion! Ingested records: {fin_res.json().get('records_ingested')}", flush=True)

    # 5. Set new dataset as active
    act_res = requests.post(f"{BASE_URL}/api/v1/datasets/active", json={"dataset_id": upload_id, "filename": "q1_q2_secondary_dataset.csv"}, headers=headers)
    assert act_res.status_code == 200, f"Set active failed: {act_res.text}"
    print(f"[4] Switched active dataset to: {upload_id}", flush=True)

    # 6. Verify Dashboard recalculates dynamically from second dataset
    summary_new = requests.get(f"{BASE_URL}/api/v1/pl/summary", headers=headers).json()
    k_new = summary_new["kpis"]
    print(f"[5] Recalculated KPIs for Secondary Dataset:", flush=True)
    print(f"    Total Revenue: Rs {k_new['revenue']:,.2f}", flush=True)
    print(f"    Total Expense: Rs {k_new['expense']:,.2f}", flush=True)
    print(f"    Net Profit:    Rs {k_new['profit']:,.2f}", flush=True)
    assert k_new['revenue'] == 6000000.0, f"Expected 6,000,000 revenue, got {k_new['revenue']}"
    assert k_new['expense'] == 3480000.0, f"Expected 3,480,000 expense, got {k_new['expense']}"
    assert k_new['profit'] == 2520000.0, f"Expected 2,520,000 profit, got {k_new['profit']}"

    # Verify Dept Performance for second dataset
    dp_new = requests.get(f"{BASE_URL}/api/v1/pl/department-performance?metric=profit&limit=top5", headers=headers).json()
    print(f"[6] Recalculated Dept Performance: Top = {dp_new['departments'][0]} (Rs {dp_new['values'][0]:,.2f})", flush=True)
    assert dp_new['departments'][0] == "Commercial"

    # 7. Restore Seeded Dataset
    seeded_id = "899540e5-fa49-49e8-b87a-6965b44fd71f"
    res_restore = requests.post(f"{BASE_URL}/api/v1/datasets/active", json={"dataset_id": seeded_id, "filename": "unified_pnl_enterprise_demo.xlsx"}, headers=headers)
    assert res_restore.status_code == 200
    print(f"[7] Successfully restored Seeded Dataset active ID: {seeded_id}", flush=True)

    # 8. Re-verify Seeded Dataset numbers
    summ_restored = requests.get(f"{BASE_URL}/api/v1/pl/summary", headers=headers).json()
    k_rest = summ_restored["kpis"]
    print(f"[8] Seeded Dataset Verified After Switch:", flush=True)
    print(f"    Revenue: Rs {k_rest['revenue']/1e7:.2f} Cr (Rs {k_rest['revenue']:,.2f})", flush=True)
    print(f"    Expense: Rs {k_rest['expense']/1e7:.2f} Cr (Rs {k_rest['expense']:,.2f})", flush=True)
    print(f"    Profit:  Rs {k_rest['profit']/1e7:.2f} Cr (Rs {k_rest['profit']:,.2f})", flush=True)
    assert abs(k_rest['revenue'] - 277988276.87) < 1.0
    assert abs(k_rest['expense'] - 198066136.85) < 1.0
    assert abs(k_rest['profit'] - 79922140.02) < 1.0
    print("\n>>> SECOND DATASET INGESTION & DYNAMIC RECALCULATION TEST PASSED 100%! <<<", flush=True)

if __name__ == "__main__":
    run_test()
