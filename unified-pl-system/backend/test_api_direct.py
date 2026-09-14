"""
Direct API test script - calls the backend endpoints directly, bypassing browser.
Credentials: admin / admin123
"""
import urllib.request
import urllib.parse
import json

BASE = "http://127.0.0.1:8000"

# Step 1: Get auth token
print("=" * 60)
print("STEP 1: Authenticate")
print("=" * 60)

def run_direct_tests():
    login_payload = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            auth_resp = json.loads(r.read().decode())
        token = auth_resp.get("access_token")
        print(f"Token obtained: {token[:50]}...")
    except Exception as e:
        print(f"Auth FAILED: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}


    # Step 2: Call active dataset
    print("\n" + "=" * 60)
    print("STEP 2: Check Active Dataset")
    print("=" * 60)
    req2 = urllib.request.Request(f"{BASE}/api/v1/datasets/active", headers=headers)
    try:
        with urllib.request.urlopen(req2) as r:
            active = json.loads(r.read().decode())
        print(f"Active dataset: {json.dumps(active, indent=2)}")
    except Exception as e:
        print(f"Active dataset call FAILED: {e}")

    # Step 3: Call PL summary
    print("\n" + "=" * 60)
    print("STEP 3: Call /api/v1/pl/summary")
    print("=" * 60)
    req3 = urllib.request.Request(f"{BASE}/api/v1/pl/summary", headers=headers)
    try:
        with urllib.request.urlopen(req3) as r:
            summary = json.loads(r.read().decode())
        kpis = summary.get("kpis", {})
        print("KPIs from API:")
        print(f"  revenue:      {kpis.get('revenue')}")
        print(f"  expense:      {kpis.get('expense')}")
        print(f"  profit:       {kpis.get('profit')}")
        print(f"  health_score: {kpis.get('health_score')}")
        periods = summary.get("periods", [])
        domains = summary.get("domains", [])
        print(f"\n  periods count: {len(periods)}")
        print(f"  domains count: {len(domains)}")
        if periods:
            print(f"  First period: {periods[0]}")
        if domains:
            print(f"  First domain: {domains[0]}")
    except Exception as e:
        print(f"Summary call FAILED: {e}")

    # Step 4: Call anomalies
    print("\n" + "=" * 60)
    print("STEP 4: Call /api/v1/anomalies/")
    print("=" * 60)
    req4 = urllib.request.Request(f"{BASE}/api/v1/anomalies/", headers=headers)
    try:
        with urllib.request.urlopen(req4) as r:
            anomalies_resp = json.loads(r.read().decode())
        anomalies = anomalies_resp.get("anomalies", anomalies_resp if isinstance(anomalies_resp, list) else [])
        print(f"  Anomalies count: {len(anomalies)}")
        if anomalies:
            print(f"  First anomaly: {json.dumps(anomalies[0], indent=4)}")
    except Exception as e:
        print(f"Anomalies call FAILED: {e}")

    # Step 5: Call anomaly trend
    print("\n" + "=" * 60)
    print("STEP 5: Call /api/v1/anomalies/trend")
    print("=" * 60)
    req5 = urllib.request.Request(f"{BASE}/api/v1/anomalies/trend", headers=headers)
    try:
        with urllib.request.urlopen(req5) as r:
            trend_resp = json.loads(r.read().decode())
        print(f"  Trend response: {json.dumps(trend_resp, indent=2)[:500]}")
    except Exception as e:
        print(f"Anomaly trend FAILED: {e}")

    # Step 6: Call forecast
    print("\n" + "=" * 60)
    print("STEP 6: Call /api/v1/pl/forecast")
    print("=" * 60)
    req6 = urllib.request.Request(f"{BASE}/api/v1/pl/forecast", headers=headers)
    try:
        with urllib.request.urlopen(req6) as r:
            forecast_resp = json.loads(r.read().decode())
        print(f"  Status: {forecast_resp.get('status')}")
        print(f"  predicted_profit_next_12: {forecast_resp.get('predicted_profit_next_12_months_in_crores')}")
        print(f"  confidence_score: {forecast_resp.get('confidence_score')}")
        print(f"  model_used: {forecast_resp.get('model_used')}")
        hist = forecast_resp.get("historical", [])
        fcast = forecast_resp.get("forecast", [])
        print(f"  historical count: {len(hist)}")
        print(f"  forecast count: {len(fcast)}")
    except Exception as e:
        print(f"Forecast call FAILED: {e}")

    print("\nDone.")

if __name__ == "__main__":
    run_direct_tests()

