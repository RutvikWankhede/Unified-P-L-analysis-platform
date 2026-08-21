import urllib.request
import urllib.error
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def check_endpoint(name, path, method="GET", data=None, headers=None, expected_status=[200, 401, 422, 400]):
    """
    Checks an endpoint.
    Since we are just doing a startup health check, we accept 401 (Unauthorized) 
    or 422/400 (Bad Request/Validation Error) as a sign that the endpoint exists 
    and the app is alive (i.e. not 404 Not Found or 500 Internal Server Error).
    """
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method=method)
    
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    
    if data:
        req.data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
        
    try:
        urllib.request.urlopen(req, timeout=5)
        return True, "Healthy"
    except urllib.error.HTTPError as e:
        if e.code in expected_status:
            return True, f"Healthy (Returned {e.code})"
        return False, f"Failed (HTTP {e.code})"
    except urllib.error.URLError as e:
        return False, f"Failed ({e.reason})"
    except Exception as e:
        return False, f"Failed ({e})"

def run_health_checks():
    endpoints = [
        ("Login", "/api/v1/auth/login", "POST", {"username": "admin", "password": "wrong_password"}),
        ("Summary", "/api/v1/pl/summary", "GET", None),
        ("Charts", "/api/v1/pl/charts", "GET", None),
        ("Forecast", "/api/v1/pl/forecast?domain=Marketing", "GET", None),
        ("Upload", "/api/v1/pl/upload", "POST", None),
        ("Reports", "/api/v1/reports/csv", "GET", None),
        ("Anomalies", "/api/v1/anomalies", "GET", None),
        ("Copilot", "/api/v1/explanations/copilot", "POST", {"question": "test"}),
        ("Workflow", "/api/v1/pl/workflows", "GET", None),
    ]

    all_healthy = True
    print("\nRunning API Health Checks...")
    for name, path, method, data in endpoints:
        is_healthy, msg = check_endpoint(name, path, method, data)
        status_str = "[SUCCESS]" if is_healthy else "[FAIL]"
        print(f"{status_str} {name:10}: {msg}")
        if not is_healthy:
            all_healthy = False
            
    return all_healthy

if __name__ == "__main__":
    time.sleep(2) # Give backend a moment if just started
    success = run_health_checks()
    sys.exit(0 if success else 1)
