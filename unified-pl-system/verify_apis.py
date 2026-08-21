import os
import re

FRONTEND_DIR = "../frontend_v2/js"
BACKEND_DIR = "backend/routers"

def get_backend_routes():
    routes = set()
    regex = r'@router\.(?:get|post|put|delete|patch)\([\'"]([/a-zA-Z0-9_\{\}\-]+)[\'"]'
    for root, _, files in os.walk(BACKEND_DIR):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.finditer(regex, content)
                    for m in matches:
                        endpoint = m.group(1)
                        # Assume prefix based on router, usually /api/v1/something
                        # To simplify, we'll just check if the ending part matches
                        routes.add(endpoint)
    return routes

def scan_frontend_apis():
    found_endpoints = set()
    regex = r"['\"](/api/v1/[a-zA-Z0-9_\-/]+)(?:\?.*)?['\"]|[`]((?:/api/v1/[a-zA-Z0-9_\-/]+)(?:\?.*)?)?.*[`]"
    
    if not os.path.exists(FRONTEND_DIR):
        return set()

    for root, _, files in os.walk(FRONTEND_DIR):
        for file in files:
            if file.endswith(".js"):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.finditer(regex, content)
                    for m in matches:
                        endpoint = m.group(1) or m.group(2)
                        if endpoint:
                            endpoint = re.sub(r'\$\{.*?\}', '{id}', endpoint)
                            found_endpoints.add(endpoint)
    return found_endpoints

if __name__ == "__main__":
    backend_routes = get_backend_routes()
    frontend_endpoints = scan_frontend_apis()

    print("=== API AUDIT REPORT ===")
    print(f"Found {len(frontend_endpoints)} frontend endpoints.")
    print(f"Found {len(backend_routes)} backend route suffixes.")
    
    # Just printing them for manual verification since static matching of prefixes is hard without FastAPI
    print("\n[FRONTEND ENDPOINTS]")
    for f in sorted(list(frontend_endpoints)):
        print(f)
        
    print("\n[BACKEND ROUTE SUFFIXES]")
    for b in sorted(list(backend_routes)):
        print(b)
