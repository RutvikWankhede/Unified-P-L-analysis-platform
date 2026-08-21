"""
run_project.py - Unified P&L Intelligence Platform Launcher
=============================================================
Starts the backend, frontend, verifies health, and opens browser.
Usage: python run_project.py
"""

import os
import sys
import time
import json
import subprocess
import threading
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "unified-pl-system" / "backend"
FRONTEND_DIR = BASE_DIR / "frontend_v2"
VENV_DIR = BASE_DIR / "unified-pl-system" / "venv"

BACKEND_PORT = 8000
FRONTEND_PORT = 3000
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}"
SWAGGER_URL = f"{BACKEND_URL}/docs"
LOGIN_URL = f"{FRONTEND_URL}/login.html"

HEALTH_TIMEOUT = 30  # seconds to wait for backend
HEALTH_INTERVAL = 1  # seconds between checks

# ─── Colors ───────────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
CHECK  = "✓"
CROSS  = "✗"
ARROW  = "→"
SPIN   = ["⠋", "⠙", "⠸", "⢰", "⡰", "⠸", "⠙", "⠋"]

def ok(msg): print(f"  {GREEN}{CHECK}{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}!{RESET} {msg}")
def err(msg): print(f"  {RED}{CROSS}{RESET} {msg}")
def info(msg): print(f"  {CYAN}{ARROW}{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{CYAN}{msg}{RESET}")

# ─── Helpers ──────────────────────────────────────────────────────────────────

def find_python():
    """Find the correct Python executable (prefer venv)."""
    venv_python = VENV_DIR / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    # Fallback to system python
    for name in ["python", "python3"]:
        try:
            result = subprocess.run([name, "--version"], capture_output=True)
            if result.returncode == 0:
                return name
        except FileNotFoundError:
            continue
    return sys.executable

def check_url(url, timeout=5):
    """Return True if URL responds with 2xx."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status < 400
    except urllib.error.HTTPError as e:
        return e.code < 500
    except Exception:
        return False

def post_json(url, data, timeout=5):
    """POST JSON to URL and return parsed response."""
    payload = json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())

def wait_for_url(url, timeout=HEALTH_TIMEOUT, label="service"):
    """Poll until URL is healthy or timeout."""
    start = time.time()
    spin_i = 0
    while time.time() - start < timeout:
        if check_url(url):
            return True
        sys.stdout.write(f"\r  {SPIN[spin_i % len(SPIN)]} Waiting for {label}…")
        sys.stdout.flush()
        spin_i += 1
        time.sleep(HEALTH_INTERVAL)
    print()
    return False

# ─── Phase 1: Environment Check ───────────────────────────────────────────────

def check_environment():
    header("Phase 1 — Environment Check")
    
    python = find_python()
    info(f"Python: {python}")
    
    # Check backend directory
    if not BACKEND_DIR.exists():
        err(f"Backend directory not found: {BACKEND_DIR}")
        sys.exit(1)
    ok("Backend directory found")
    
    if not FRONTEND_DIR.exists():
        err(f"Frontend directory not found: {FRONTEND_DIR}")
        sys.exit(1)
    ok("Frontend directory found")
    
    # Check .env
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        warn(".env not found — creating default")
        env_file.write_text(
            f"DATABASE_URL=sqlite:///./enterprise_pl.db\n"
            f"SECRET_KEY=supersecretkey-unified-pl-2025\n"
            f"ALLOWED_ORIGINS=http://localhost:{FRONTEND_PORT},http://127.0.0.1:{FRONTEND_PORT}\n"
            f"GEMINI_API_KEY=\n"
        )
        ok(".env created with defaults")
    else:
        ok(".env found")
    
    return python

# ─── Phase 2: Database & Seed ─────────────────────────────────────────────────

def setup_database(python):
    header("Phase 2 — Database Setup")
    
    db_file = BACKEND_DIR / "enterprise_pl.db"
    
    # Run seed.py (idempotent)
    info("Running seed.py to ensure demo data…")
    result = subprocess.run(
        [python, "seed.py"],
        cwd=str(BACKEND_DIR),
        capture_output=True, text=True
    )
    if result.returncode == 0:
        ok(f"Seed: {result.stdout.strip() or 'OK'}")
    else:
        warn(f"Seed warning: {result.stderr.strip()[:100]}")
    
    if db_file.exists():
        size_mb = db_file.stat().st_size / (1024 * 1024)
        ok(f"Database: enterprise_pl.db ({size_mb:.1f} MB)")
    else:
        err("Database file not found after seed!")

# ─── Phase 3: Backend ─────────────────────────────────────────────────────────

backend_proc = None

def start_backend(python):
    global backend_proc
    header("Phase 3 — Starting Backend")
    
    # Kill any existing process on port 8000
    try:
        subprocess.run(
            ["powershell", "-Command", f"Get-NetTCPConnection -LocalPort {BACKEND_PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass
    
    time.sleep(1)
    
    info(f"Starting FastAPI backend on port {BACKEND_PORT}…")
    
    log_file = open(BASE_DIR / "backend.log", "w")
    backend_proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=str(BACKEND_DIR),
        stdout=log_file,
        stderr=log_file,
    )
    
    if wait_for_url(f"{BACKEND_URL}/", label="backend"):
        print()
        ok(f"Backend running at {BACKEND_URL}")
    else:
        print()
        err("Backend failed to start. Check backend.log")
        # Show last few lines of log
        try:
            with open(BASE_DIR / "backend.log") as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print("  ", line.rstrip())
        except Exception:
            pass
        cleanup()
        sys.exit(1)

# ─── Phase 4: Health Check ────────────────────────────────────────────────────

def verify_health():
    header("Phase 4 — API Health Verification")
    
    all_ok = True
    endpoints = [
        (f"{BACKEND_URL}/docs", "Swagger UI"),
        (f"{BACKEND_URL}/api/v1/system/health", "Health endpoint"),
    ]
    
    for url, label in endpoints:
        if check_url(url):
            ok(label)
        else:
            warn(f"{label} not responding (non-fatal)")
    
    # Test JWT login
    info("Testing JWT authentication (admin/admin123)…")
    try:
        resp = post_json(f"{BACKEND_URL}/api/v1/auth/login", {"username": "admin", "password": "admin123"})
        if resp.get("access_token"):
            ok("JWT authentication working")
            token = resp["access_token"]
        else:
            warn("Login returned no token")
            token = None
    except Exception as e:
        warn(f"Auth test failed: {e}")
        token = None
        all_ok = False
    
    # Test protected APIs
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        protected = [
            ("/api/v1/pl/summary", "P&L Summary"),
            ("/api/v1/pl/charts", "Charts"),
            ("/api/v1/anomalies/", "Anomalies"),
            ("/api/v1/recommendations/", "Recommendations"),
            ("/api/v1/pl/workflows", "Workflows"),
        ]
        for path, label in protected:
            try:
                req = urllib.request.Request(f"{BACKEND_URL}{path}", headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        ok(label)
                    else:
                        warn(f"{label}: HTTP {resp.status}")
            except Exception as e:
                warn(f"{label}: {str(e)[:50]}")
    
    return all_ok

# ─── Phase 5: Frontend ────────────────────────────────────────────────────────

frontend_proc = None

def start_frontend(python):
    global frontend_proc
    header("Phase 5 — Starting Frontend")
    
    # Kill any existing process on port 3000
    try:
        subprocess.run(
            ["powershell", "-Command", f"Get-NetTCPConnection -LocalPort {FRONTEND_PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass
    
    time.sleep(1)
    
    info(f"Starting HTTP frontend server on port {FRONTEND_PORT}…")
    
    log_file = open(BASE_DIR / "frontend.log", "w")
    frontend_proc = subprocess.Popen(
        [python, "-m", "http.server", str(FRONTEND_PORT)],
        cwd=str(FRONTEND_DIR),
        stdout=log_file,
        stderr=log_file,
    )
    
    if wait_for_url(f"{FRONTEND_URL}/login.html", label="frontend"):
        print()
        ok(f"Frontend running at {FRONTEND_URL}")
    else:
        print()
        err("Frontend failed to start. Check frontend.log")
        cleanup()
        sys.exit(1)

# ─── Phase 6: Open Browser ────────────────────────────────────────────────────

def open_browser():
    header("Phase 6 — Opening Browser")
    
    time.sleep(1)
    
    for url in [SWAGGER_URL, FRONTEND_URL, LOGIN_URL]:
        info(f"Opening {url}")
        webbrowser.open(url)
        time.sleep(0.5)

# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary():
    header("=" * 55)
    print(f"""
{BOLD}{GREEN}  ✓ Unified P&L Intelligence Platform is RUNNING{RESET}
{BOLD}{'=' * 55}{RESET}

  {BOLD}Frontend:{RESET}   {CYAN}{LOGIN_URL}{RESET}
  {BOLD}Backend:{RESET}    {CYAN}{BACKEND_URL}{RESET}
  {BOLD}Swagger:{RESET}    {CYAN}{SWAGGER_URL}{RESET}

  {BOLD}Demo Credentials:{RESET}
    Username: {GREEN}admin{RESET}
    Password: {GREEN}admin123{RESET}

  {BOLD}Logs:{RESET}
    Backend:  backend.log
    Frontend: frontend.log

  Press {BOLD}Ctrl+C{RESET} to stop all servers.
{BOLD}{'=' * 55}{RESET}
""")

# ─── Cleanup ──────────────────────────────────────────────────────────────────

def cleanup():
    print(f"\n{YELLOW}Shutting down servers…{RESET}")
    global backend_proc, frontend_proc
    for proc in [backend_proc, frontend_proc]:
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try: proc.kill()
                except Exception: pass

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════╗
║   Unified P&L Intelligence — Launcher       ║
║   Enterprise AI Financial Platform          ║
╚══════════════════════════════════════════════╝{RESET}
""")
    
    python = check_environment()
    setup_database(python)
    start_backend(python)
    verify_health()
    start_frontend(python)
    open_browser()
    print_summary()
    
    # Keep alive
    try:
        while True:
            if backend_proc and backend_proc.poll() is not None:
                err("Backend crashed! Restarting…")
                start_backend(python)
            if frontend_proc and frontend_proc.poll() is not None:
                err("Frontend crashed! Restarting…")
                start_frontend(python)
            time.sleep(10)
    except KeyboardInterrupt:
        cleanup()
        print(f"\n{GREEN}Goodbye!{RESET}\n")

if __name__ == "__main__":
    main()
