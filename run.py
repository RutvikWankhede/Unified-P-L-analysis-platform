"""
run.py - Production Launcher for Unified P&L Intelligence Platform
==================================================================
Clean, robust launcher built around real subprocess.Popen child handles.
- Resolves all paths relative to Path(__file__).resolve().parent
- Supports Windows, Linux, and macOS
- Detects or automatically creates virtual environment
- Validates dependencies and imports before launching Uvicorn
- Lightweight readiness check using /api/v1/system/health and /login.html
- Direct child process lifecycle management with graceful shutdown on Ctrl+C
- No blind PID killing or restart loops

Usage:
    python run.py                      # Normal launch
    python run.py --self-test          # Test startup and readiness, then exit
    python run.py --no-browser         # Start servers without launching browser
    python run.py --seed               # Force database seed before launch
    python run.py --backend-port 8000  # Custom backend port
    python run.py --frontend-port 3000 # Custom frontend port
    python run.py --diag               # Environment diagnostics only
"""

from __future__ import annotations

import argparse
import atexit
import io
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Force UTF-8 output on Windows to prevent cp1252 encoding errors
if sys.platform == "win32":
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ANSI colors (VT sequences enabled on Windows 10+)
os.system("")
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SPIN = ["-", "\\", "|", "/"]

def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET}   {msg}", flush=True)

def warn(msg: str) -> None:
    print(f"  {YELLOW}[WARN]{RESET} {msg}", flush=True)

def err(msg: str) -> None:
    print(f"  {RED}[ERR]{RESET}  {msg}", flush=True)

def info(msg: str) -> None:
    print(f"  {CYAN}[INFO]{RESET} {msg}", flush=True)

def header(msg: str) -> None:
    bar = "=" * len(msg)
    print(f"\n{BOLD}{CYAN}{bar}\n{msg}\n{bar}{RESET}", flush=True)

# ──────────────────────────────────────────────────────────────────────────────
# PATH DISCOVERY & ENVIRONMENT HELPERS
# ──────────────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent

def find_backend_dir() -> Path | None:
    """Find directory containing main.py with FastAPI app."""
    candidates = [
        ROOT_DIR / "unified-pl-system" / "backend",
        ROOT_DIR / "backend",
    ]
    for p in candidates:
        if p.exists() and (p / "main.py").exists():
            return p
    return None

def find_frontend_dir() -> Path | None:
    """Find directory containing login.html."""
    candidates = [
        ROOT_DIR / "frontend_v2",
        ROOT_DIR / "unified-pl-system" / "frontend_v2",
        ROOT_DIR / "frontend",
    ]
    for p in candidates:
        if p.exists() and (p / "login.html").exists():
            return p
    return None

def resolve_or_create_venv() -> Path:
    """Locate virtual environment Python or create one if missing."""
    candidates = [
        ROOT_DIR / "unified-pl-system" / "venv",
        ROOT_DIR / "venv",
        ROOT_DIR / ".venv",
        ROOT_DIR / "unified-pl-system" / ".venv",
    ]
    for venv_dir in candidates:
        if sys.platform == "win32":
            py_exe = venv_dir / "Scripts" / "python.exe"
        else:
            py_exe = venv_dir / "bin" / "python"
        if py_exe.exists():
            return py_exe

    # If not found, create a new venv in unified-pl-system/venv
    target_venv = ROOT_DIR / "unified-pl-system" / "venv"
    info(f"No existing virtualenv found. Creating virtualenv at {target_venv}...")
    target_venv.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "venv", str(target_venv)], check=True)

    if sys.platform == "win32":
        py_exe = target_venv / "Scripts" / "python.exe"
    else:
        py_exe = target_venv / "bin" / "python"
    
    ok(f"Virtualenv created: {py_exe}")
    return py_exe

def build_backend_env(backend_dir: Path) -> dict[str, str]:
    """Construct environment dictionary with backend on PYTHONPATH and .env loaded."""
    env = os.environ.copy()
    backend_str = str(backend_dir)
    existing_py_path = env.get("PYTHONPATH", "")
    if existing_py_path:
        env["PYTHONPATH"] = backend_str + os.pathsep + existing_py_path
    else:
        env["PYTHONPATH"] = backend_str

    # Load .env variables if present
    env_file = backend_dir / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip()
                    if k and k not in env:
                        env[k] = v
        except Exception as e:
            warn(f"Failed to read .env file: {e}")
    return env

def ensure_dependencies(python_exe: Path, backend_dir: Path) -> bool:
    """Verify core dependencies and install from requirements.txt if missing."""
    test_code = "import fastapi, uvicorn, sqlalchemy, pydantic"
    res = subprocess.run(
        [str(python_exe), "-c", test_code],
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        ok("Core dependencies available (fastapi, uvicorn, sqlalchemy, pydantic)")
        return True

    req_file = backend_dir / "requirements.txt"
    if not req_file.exists():
        req_file = ROOT_DIR / "requirements.txt"

    if not req_file.exists():
        err(f"Dependencies missing and requirements.txt not found in {backend_dir}")
        return False

    info(f"Installing dependencies from {req_file}...")
    install_res = subprocess.run(
        [str(python_exe), "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if install_res.returncode != 0:
        err(f"Dependency installation failed:\n{install_res.stderr}")
        return False

    ok("Dependencies successfully installed")
    return True

def validate_main_module(python_exe: Path, backend_dir: Path, backend_env: dict[str, str]) -> bool:
    """Validate that main.py can be imported and contains the FastAPI app object."""
    info("Validating backend entrypoint (main:app)...")
    code = (
        "import sys\n"
        "sys.path.insert(0, '.')\n"
        "import main\n"
        "assert hasattr(main, 'app'), 'main.py missing FastAPI app object'\n"
        "print('MAIN_APP_OK')\n"
    )
    res = subprocess.run(
        [str(python_exe), "-c", code],
        cwd=str(backend_dir),
        env=backend_env,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0 and "MAIN_APP_OK" in res.stdout:
        ok("Backend module and app object validated")
        return True

    err("Backend validation failed. Detailed diagnostic:")
    print(f"{RED}{'='*60}")
    if res.stderr:
        for line in res.stderr.strip().splitlines():
            print(f"  {line}")
    elif res.stdout:
        for line in res.stdout.strip().splitlines():
            print(f"  {line}")
    print(f"{'='*60}{RESET}")
    return False

def setup_database_if_needed(python_exe: Path, backend_dir: Path, backend_env: dict[str, str], force_seed: bool = False) -> bool:
    """Run database seeding only if database file does not exist or force_seed is True."""
    db_file = backend_dir / "enterprise_pl.db"
    seed_file = backend_dir / "seed.py"
    
    if not seed_file.exists():
        info("No seed.py found, skipping database seed")
        return True

    if db_file.exists() and not force_seed:
        ok(f"Database exists ({db_file.name}) — skipping seed for fast startup")
        return True

    info("Seeding database...")
    res = subprocess.run(
        [str(python_exe), "seed.py"],
        cwd=str(backend_dir),
        env=backend_env,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        ok("Database seed completed")
        return True
    else:
        err(f"Database seed failed:\n{res.stderr or res.stdout}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
# NETWORKING & READINESS HELPERS
# ──────────────────────────────────────────────────────────────────────────────

_no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def is_port_available(port: int) -> bool:
    """Test if a port can be bound exclusively on 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False

def check_endpoint_ready(
    url: str,
    proc: subprocess.Popen,
    timeout: float = 30.0,
    label: str = "Service",
    log_path: Path | None = None,
) -> bool:
    """Poll an HTTP endpoint until ready or until child process exits/times out."""
    start_time = time.time()
    idx = 0
    backoff = 0.2

    while time.time() - start_time < timeout:
        # Check if the child process exited prematurely
        ret = proc.poll()
        if ret is not None:
            print()
            err(f"{label} process exited prematurely (exit code: {ret})")
            if log_path and log_path.exists():
                _dump_log_tail(log_path)
            return False

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PL-Launcher-HealthCheck"})
            with _no_proxy_opener.open(req, timeout=1.5) as resp:
                if resp.status == 200:
                    print()
                    ok(f"{label} is healthy and responding (HTTP 200)")
                    return True
        except Exception:
            pass

        sys.stdout.write(f"\r  {SPIN[idx % 4]} Waiting for {label}... ({int(time.time() - start_time)}s)")
        sys.stdout.flush()
        idx += 1
        time.sleep(backoff)
        backoff = min(0.8, backoff * 1.1)

    print()
    if proc.poll() is None:
        err(f"{label} process is still running (PID {proc.pid}) but not healthy after {timeout}s timeout")
    else:
        err(f"{label} process exited with return code {proc.poll()}")

    if log_path and log_path.exists():
        _dump_log_tail(log_path)
    return False

def _dump_log_tail(log_path: Path, max_lines: int = 40) -> None:
    """Display the last lines of a log file for diagnosis."""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        print(f"\n  {BOLD}{'─'*50}")
        print(f"  Log Tail ({log_path.name}):")
        print(f"  {'─'*50}{RESET}")
        for line in lines[-max_lines:]:
            print(f"    {line}")
        print()
    except Exception as e:
        warn(f"Could not read log file {log_path}: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# PROCESS MANAGEMENT & CLEANUP
# ──────────────────────────────────────────────────────────────────────────────

class ProcessManager:
    def __init__(self):
        self.backend_proc: subprocess.Popen | None = None
        self.frontend_proc: subprocess.Popen | None = None
        self.backend_log_file = None
        self.frontend_log_file = None

    def terminate_proc(self, proc: subprocess.Popen | None, name: str) -> None:
        if proc is None:
            return
        if proc.poll() is not None:
            return
        try:
            info(f"Stopping {name} (PID {proc.pid})...")
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
        except Exception:
            pass

    def cleanup(self) -> None:
        self.terminate_proc(self.backend_proc, "backend")
        self.terminate_proc(self.frontend_proc, "frontend")
        self.backend_proc = None
        self.frontend_proc = None

        for fh in [self.backend_log_file, self.frontend_log_file]:
            if fh:
                try:
                    fh.close()
                except Exception:
                    pass
        self.backend_log_file = None
        self.frontend_log_file = None

manager = ProcessManager()

def _cleanup_handler():
    manager.cleanup()

atexit.register(_cleanup_handler)

def handle_sigint(signum, frame):
    info("Shutdown signal received. Exiting...")
    manager.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, handle_sigint)

# ──────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS & SUMMARY
# ──────────────────────────────────────────────────────────────────────────────

def run_diagnostics(backend_dir: Path | None, frontend_dir: Path | None, python_exe: Path, be_port: int, fe_port: int) -> None:
    header("DIAGNOSTICS REPORT")
    print(f"  {BOLD}Root directory:{RESET}      {ROOT_DIR}")
    print(f"  {BOLD}Backend directory:{RESET}   {backend_dir or 'NOT FOUND'}")
    print(f"  {BOLD}Frontend directory:{RESET}  {frontend_dir or 'NOT FOUND'}")
    print(f"  {BOLD}Python executable:{RESET}   {python_exe}")
    print(f"  {BOLD}Backend port {be_port}:{RESET}    {'FREE' if is_port_available(be_port) else 'IN USE'}")
    print(f"  {BOLD}Frontend port {fe_port}:{RESET}   {'FREE' if is_port_available(fe_port) else 'IN USE'}")
    print()

def print_summary(frontend_port: int, backend_port: int) -> None:
    print(f"""
{BOLD}{GREEN}====================================================={RESET}
{BOLD}{GREEN}  Unified P&L Intelligence Platform — RUNNING        {RESET}
{BOLD}{GREEN}====================================================={RESET}

  {BOLD}Frontend:{RESET}   {CYAN}http://127.0.0.1:{frontend_port}/login.html{RESET}
  {BOLD}Backend:{RESET}    {CYAN}http://127.0.0.1:{backend_port}{RESET}
  {BOLD}API Docs:{RESET}   {CYAN}http://127.0.0.1:{backend_port}/docs{RESET}
  {BOLD}Health:{RESET}     {CYAN}http://127.0.0.1:{backend_port}/api/v1/system/health{RESET}

  {BOLD}Logs:{RESET}
    Backend:  backend.log
    Frontend: frontend.log

  Press {BOLD}Ctrl+C{RESET} to stop servers.
{BOLD}{GREEN}====================================================={RESET}
""", flush=True)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Unified P&L Intelligence Platform Launcher")
    parser.add_argument("--self-test", action="store_true", help="Launch servers, verify endpoints, shutdown, and exit.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser upon launch.")
    parser.add_argument("--seed", action="store_true", help="Force database seed on startup.")
    parser.add_argument("--backend-port", type=int, default=8000, help="Port for the FastAPI backend (default: 8000).")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Port for the frontend static server (default: 3000).")
    parser.add_argument("--diag", action="store_true", help="Run diagnostics and exit without starting servers.")
    args = parser.parse_args()

    print(f"""
{BOLD}{CYAN}+======================================================+
|   Unified P&L Intelligence Platform — Launcher       |
+======================================================+{RESET}
""")

    # Step 1: Project Discovery
    header("Step 1 — Project Discovery")
    backend_dir = find_backend_dir()
    if not backend_dir:
        err("Backend directory with main.py not found.")
        sys.exit(1)
    ok(f"Backend directory:  {backend_dir}")

    frontend_dir = find_frontend_dir()
    if not frontend_dir:
        err("Frontend directory with login.html not found.")
        sys.exit(1)
    ok(f"Frontend directory: {frontend_dir}")

    python_exe = resolve_or_create_venv()
    ok(f"Python runtime:     {python_exe}")

    if args.diag:
        run_diagnostics(backend_dir, frontend_dir, python_exe, args.backend_port, args.frontend_port)
        return

    # Step 2: Environment & Dependencies
    header("Step 2 — Environment & Dependency Check")
    backend_env = build_backend_env(backend_dir)
    if not ensure_dependencies(python_exe, backend_dir):
        err("Dependency verification failed.")
        sys.exit(1)

    # Step 3: Database setup
    header("Step 3 — Database Initialization")
    if not setup_database_if_needed(python_exe, backend_dir, backend_env, force_seed=args.seed):
        err("Database preparation failed.")
        sys.exit(1)

    # Step 4: Import validation
    header("Step 4 — Backend Import Validation")
    if not validate_main_module(python_exe, backend_dir, backend_env):
        err("Cannot launch: backend import error.")
        sys.exit(1)

    # Step 5: Port Check
    header("Step 5 — Port Availability Check")
    if not is_port_available(args.backend_port):
        err(f"Backend port {args.backend_port} is already in use. Please free the port and try again.")
        sys.exit(1)
    ok(f"Backend port {args.backend_port} is free")

    if not is_port_available(args.frontend_port):
        err(f"Frontend port {args.frontend_port} is already in use. Please free the port and try again.")
        sys.exit(1)
    ok(f"Frontend port {args.frontend_port} is free")

    # Step 6: Start Backend
    header("Step 6 — Starting Backend Service")
    backend_log_path = ROOT_DIR / "backend.log"
    manager.backend_log_file = open(backend_log_path, "w", encoding="utf-8")

    backend_cmd = [
        str(python_exe),
        "-u",
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.backend_port),
        "--log-level",
        "info",
    ]
    info(f"Spawning backend: {' '.join(backend_cmd)}")
    manager.backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(backend_dir),
        env=backend_env,
        stdin=subprocess.DEVNULL,
        stdout=manager.backend_log_file,
        stderr=subprocess.STDOUT,
    )
    ok(f"Backend process spawned (PID {manager.backend_proc.pid})")

    # Step 7: Await Backend Health
    header("Step 7 — Verifying Backend Readiness")
    backend_health_url = f"http://127.0.0.1:{args.backend_port}/api/v1/system/health"
    if not check_endpoint_ready(backend_health_url, manager.backend_proc, timeout=30.0, label="Backend", log_path=backend_log_path):
        err("Backend failed to reach healthy state.")
        manager.cleanup()
        sys.exit(1)

    # Step 8: Start Frontend
    header("Step 8 — Starting Frontend Service")
    frontend_log_path = ROOT_DIR / "frontend.log"
    manager.frontend_log_file = open(frontend_log_path, "w", encoding="utf-8")

    frontend_cmd = [
        str(python_exe),
        "-u",
        "-m",
        "http.server",
        str(args.frontend_port),
        "--bind",
        "127.0.0.1",
    ]
    info(f"Spawning frontend: {' '.join(frontend_cmd)}")
    manager.frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=str(frontend_dir),
        stdin=subprocess.DEVNULL,
        stdout=manager.frontend_log_file,
        stderr=subprocess.STDOUT,
    )
    ok(f"Frontend process spawned (PID {manager.frontend_proc.pid})")

    # Step 9: Await Frontend Reachability
    header("Step 9 — Verifying Frontend Readiness")
    frontend_url = f"http://127.0.0.1:{args.frontend_port}/login.html"
    if not check_endpoint_ready(frontend_url, manager.frontend_proc, timeout=15.0, label="Frontend", log_path=frontend_log_path):
        err("Frontend failed to reach ready state.")
        manager.cleanup()
        sys.exit(1)

    # If Self-Test mode:
    if args.self_test:
        header("SELF-TEST VERIFICATION COMPLETED")
        ok("Backend health endpoint HTTP 200 OK")
        ok("Frontend login page HTTP 200 OK")
        info("Shutting down child processes cleanly...")
        manager.cleanup()
        ok("Self-test passed successfully.")
        sys.exit(0)

    # Step 10: Browser Launch
    if not args.no_browser:
        header("Step 10 — Launching Browser")
        info(f"Opening {frontend_url} in default browser...")
        webbrowser.open(frontend_url)

    # Step 11: Summary and Process Supervision Loop
    print_summary(args.frontend_port, args.backend_port)

    try:
        while True:
            time.sleep(1.0)
            be_ret = manager.backend_proc.poll()
            if be_ret is not None:
                err(f"Backend process (PID {manager.backend_proc.pid}) terminated with return code {be_ret}.")
                _dump_log_tail(backend_log_path)
                break

            fe_ret = manager.frontend_proc.poll()
            if fe_ret is not None:
                err(f"Frontend process (PID {manager.frontend_proc.pid}) terminated with return code {fe_ret}.")
                _dump_log_tail(frontend_log_path)
                break
    except KeyboardInterrupt:
        pass
    finally:
        info("Shutting down servers...")
        manager.cleanup()
        ok("All services stopped cleanly.")

if __name__ == "__main__":
    main()
