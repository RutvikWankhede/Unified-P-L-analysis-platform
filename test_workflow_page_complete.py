import urllib.request
import json
import sys

def test_workflow_system():
    results = {}
    
    # 1. Test frontend workflow.html
    try:
        req = urllib.request.urlopen("http://127.0.0.1:3000/workflow.html", timeout=5)
        html = req.read().decode('utf-8')
        results["workflow.html_status"] = req.status
        results["has_sidebar_container"] = 'id="sidebar-container"' in html
        results["has_main_content"] = '<main' in html and 'ml-[240px]' in html
        results["has_workflow_js"] = 'js/workflow.js' in html
        results["has_shell_js"] = 'js/shell.js' in html
        results["has_bpmn_pipeline"] = 'BPMN 2.0 Financial Orchestration Pipeline' in html
        results["has_approval_banner"] = 'pending-approval-banner' in html
        results["has_worker_matrix"] = 'External Task Workers Matrix' in html
        results["has_agent_execution"] = 'Agent Execution & Reasoning Trace' in html
    except Exception as e:
        results["workflow.html_error"] = str(e)
        
    # 2. Test login and get JWT token
    token = None
    try:
        login_data = json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8')
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/auth/login", data=login_data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=5)
        res_json = json.loads(resp.read().decode('utf-8'))
        token = res_json.get("access_token")
        results["auth_login"] = "SUCCESS" if token else "FAILED"
    except Exception as e:
        results["auth_login"] = f"ERROR: {e}"
        
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    # 3. Test workflow endpoints
    endpoints = [
        "/api/v1/workflow/camunda-status",
        "/api/v1/workflow/instances",
        "/api/v1/workflow/engine-status",
    ]
    
    for ep in endpoints:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:8000{ep}", headers=headers)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode('utf-8'))
            results[ep] = {"status": resp.status, "data_type": type(data).__name__, "length": len(data) if isinstance(data, (list, dict)) else 1, "sample": data if not isinstance(data, list) else data[:1]}
        except Exception as e:
            results[ep] = {"error": str(e)}
            
    print("\n--- WORKFLOW TEST RESULTS ---")
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    test_workflow_system()
