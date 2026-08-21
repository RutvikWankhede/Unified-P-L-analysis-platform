import socket
import sys
import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"


def is_server_running(host="127.0.0.1", port=8000):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def test_integration():
    if not is_server_running():
        pytest.skip(
            "Backend server is not running on 127.0.0.1:8000. Skipping integration test."
        )

    print("Starting DevOps Integration Verification...")

    # Step 1: Login
    print("\n1. Testing User Login...")
    login_payload = {
        "username": "testuser",
        "password": "testpass",
        "email": "test@test.com",
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_payload)
    if response.status_code != 200:
        print(f"FAILED: Login status code {response.status_code}")
        print(response.text)
        sys.exit(1)

    token_json = response.json()
    token = token_json.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("SUCCESS: Logged in and received JWT token!")

    # Step 2: Upload CSV
    print("\n2. Testing P&L CSV Ingestion Upload...")
    csv_data = (
        "domain,period,line_item,amount,currency,cost_center\n"
        "Retail,2026-03,Sales Revenue,150000.0,USD,CC_101\n"
        "Retail,2026-03,Cost of Goods Sold,-90000.0,USD,CC_101\n"
        "Retail,2026-03,Marketing Expense,-250000.0,USD,CC_101\n"
    )
    files = {"file": ("test_pl.csv", csv_data, "text/csv")}
    response = requests.post(
        f"{BASE_URL}/api/v1/pl/upload", headers=headers, files=files
    )
    if response.status_code not in (200, 201):
        print(f"FAILED: Upload status code {response.status_code}")
        print(response.text)
        sys.exit(1)

    upload_res = response.json()
    upload_id = upload_res.get("upload_id")
    print(
        f"SUCCESS: Uploaded CSV! Upload ID: {upload_id}, Ingested: {upload_res.get('records_ingested')}"
    )

    # Step 3: Retrieve records
    print("\n3. Testing P&L Records Retrieval...")
    response = requests.get(f"{BASE_URL}/api/v1/pl/records", headers=headers)
    if response.status_code != 200:
        print(f"FAILED: Records fetch status code {response.status_code}")
        sys.exit(1)
    print(f"SUCCESS: Fetched {len(response.json().get('items', []))} records.")

    # Step 4: Retrieve Anomalies
    print("\n4. Testing Anomaly Detection pipeline...")
    response = requests.get(f"{BASE_URL}/api/v1/anomalies/", headers=headers)
    if response.status_code != 200:
        print(f"FAILED: Anomalies fetch status code {response.status_code}")
        print(response.text)
        sys.exit(1)

    anomalies = response.json()
    print(f"SUCCESS: Found {len(anomalies)} anomalies in DB.")
    anomaly_id = None
    if anomalies:
        anomaly_id = anomalies[0].get("id")
        print(f"Using anomaly ID: {anomaly_id} for further testing.")

    # Step 5: Test AI Explanations & recommendations if anomaly found
    if anomaly_id:
        print(f"\n5a. Testing AI Explanations for Anomaly {anomaly_id}...")
        response = requests.post(
            f"{BASE_URL}/api/v1/explanations/anomaly/{anomaly_id}", headers=headers
        )
        print(f"Explanation API status code: {response.status_code}")
        if response.status_code in (200, 201):
            print(
                f"SUCCESS: Explanation response: {response.json().get('root_cause')[:60]}..."
            )

        print(f"\n5b. Testing AI Recommendations for Anomaly {anomaly_id}...")
        response = requests.get(
            f"{BASE_URL}/api/v1/recommendations/anomaly/{anomaly_id}", headers=headers
        )
        print(f"Recommendations API status code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: Fetched recommendations list.")

    # Step 6: Test AI Copilot Chat
    print("\n6. Testing AI Copilot chat context endpoint...")
    copilot_query = {
        "question": "Are there any marketing anomalies in Retail domain for 2026-03?"
    }
    response = requests.post(
        f"{BASE_URL}/api/v1/explanations/copilot", headers=headers, json=copilot_query
    )
    if response.status_code != 200:
        print(f"FAILED: Copilot status code {response.status_code}")
        sys.exit(1)
    print(f"SUCCESS: Copilot responded: {response.json().get('answer')[:80]}...")

    # Step 7: Reports
    print("\n7. Testing PDF Report Generation...")
    response = requests.get(
        f"{BASE_URL}/api/v1/reports/pdf?upload_id={upload_id}", headers=headers
    )
    if response.status_code != 200:
        print(f"FAILED: PDF report status code {response.status_code}")
        sys.exit(1)
    print(f"SUCCESS: Generated PDF report! Size: {len(response.content)} bytes.")

    print("\n=========================================")
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=========================================")


if __name__ == "__main__":
    test_integration()
