import json
import urllib.request
import urllib.parse
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_API = "http://127.0.0.1:8000"
BASE_FE = "http://127.0.0.1:3000"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def test_url(url, method="GET", body=None, headers=None):
    if headers is None:
        headers = {}
    data = None
    if body is not None:
        if headers.get("Content-Type") == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(body).encode("utf-8")
        else:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=10) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            return resp.status, content
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)

print("=" * 60)
print("RUNNING COMPREHENSIVE PLATFORM VERIFICATION")
print("=" * 60)

# 1. Health
st, res = test_url(f"{BASE_API}/api/v1/system/health")
print(f"1. System Health: Status {st} -> {res[:100]}")
assert st == 200, "Health check failed"

# 2. Login to get token
st, res = test_url(
    f"{BASE_API}/api/v1/auth/login",
    method="POST",
    body={"username": "admin", "password": "admin123"},
)
print(f"2. Auth Login: Status {st}")
auth_data = json.loads(res)
token = auth_data.get("access_token")
assert token, f"Failed to obtain JWT token: {res}"
auth_headers = {"Authorization": f"Bearer {token}"}

# 3. Reports API (All 5 canonical types)
print("\n3. Testing Reports API Data for 5 canonical types:")
for rtype in ["executive", "department", "variance", "anomaly", "forecast"]:
    st, res = test_url(f"{BASE_API}/api/v1/reports/data?report_type={rtype}", headers=auth_headers)
    print(f"   Report Type '{rtype}': Status {st}")
    assert st == 200, f"Reports data failed for {rtype}: {res}"
    parsed = json.loads(res)
    kpis = parsed.get("kpis", {})
    rows = parsed.get("departments", [])
    print(f"     -> KPIs: {list(kpis.keys())}")
    print(f"     -> Rows: {len(rows)} department rows")
    assert len(rows) > 0, f"Report {rtype} returned empty rows"

# 4. Copilot Multi-Objective Benchmark
queries = [
    "which department has best profit and least anomalies",
    "which department has lowest profit and most anomalies",
    "compare Sales and Marketing",
    "why did profit decline in R&D",
    "give me an executive summary of financial performance"
]

print("\n4. Testing Copilot Multi-Objective & Analytical Queries:")
for q in queries:
    st, res = test_url(
        f"{BASE_API}/api/v1/copilot/chat",
        method="POST",
        body={"question": q, "session_id": "test-session"},
        headers=auth_headers
    )
    assert st == 200, f"Copilot chat failed for query: {q}: {res}"
    parsed = json.loads(res)
    answer = parsed.get("answer", "")
    print(f"\n   Q: {q}")
    print(f"   A: {answer[:250]}...")
    if "best profit and least anomalies" in q:
        assert "Engineering" in answer or "Sales" in answer or "Joint Leader" in answer or "Pareto" in answer, "Best profit did not identify proper top department"
        assert "Human Resources currently has the lowest net profit" not in answer, "Regression: lowest profit returned for best profit question!"

# 5. Frontend static pages
fe_pages = ["/login.html", "/dashboard.html", "/reports.html", "/anomalies.html", "/forecast.html", "/copilot.html"]
print("\n5. Testing Frontend Static HTML Pages:")
for p in fe_pages:
    st, res = test_url(f"{BASE_FE}{p}")
    print(f"   Page {p}: Status {st}")
    assert st == 200, f"Page {p} not accessible"

print("\n" + "=" * 60)
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY (100% PASS)")
print("=" * 60)
