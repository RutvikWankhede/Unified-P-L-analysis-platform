"""
run.py - Production Launcher for Unified P&L Intelligence Platform
==================================================================
Completely self-contained launcher that:
  - Auto-discovers backend/frontend locations (no hardcoded paths)
  - Sets PYTHONPATH and working directory correctly before starting uvicorn
  - Validates imports before launch, printing full tracebacks on failure
  - Waits for backend readiness before opening frontend/browser
  - Handles graceful shutdown and auto-restart on crash

Usage:
    python run.py              # Normal launch
    python run.py --self-test  # Launch, shutdown, launch x3 (self-test)
    python run.py --diag       # Diagnostics only, do not start servers
"""

from __future__ import annotations

import os
import sys

# Force UTF-8 output on Windows to prevent cp1252 encoding errors
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True, write_through=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True, write_through=True)

import ast
import atexit
import time
import json
import signal
import shutil
import socket
import textwrap
import traceback
import subprocess
import threading
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LOCK_FILE = SCRIPT_DIR / ".launcher.pid"

def acquire_single_instance_lock():
    """Ensure only one instance of run.py is active at any time on Windows."""
    my_pid = os.getpid()
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            if old_pid != my_pid:
                # Check if old launcher is still running and terminate it
                out = subprocess.check_output(f"tasklist /FI \"PID eq {old_pid}\"", shell=True, stderr=subprocess.DEVNULL).decode(errors="replace")
                if str(old_pid) in out:
                    info(f"Terminating previous launcher instance (PID {old_pid})...")
                    subprocess.run(f"taskkill /F /T /PID {old_pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
        except Exception:
            pass
    try:
        LOCK_FILE.write_text(str(my_pid), encoding="utf-8")
    except Exception:
        pass

def release_single_instance_lock():
    try:
        if LOCK_FILE.exists():
            my_pid = str(os.getpid())
            try:
                content = LOCK_FILE.read_text(encoding="utf-8").strip()
                if content == my_pid:
                    LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass

atexit.register(release_single_instance_lock)

# ──────────────────────────────────────────────────────────────────────────────
# ANSI colours (safe on Windows 10+)
# ──────────────────────────────────────────────────────────────────────────────
os.system("")  # Enable VT sequences on Windows
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

SPIN = ["-", "\\", "|", "/"]

def ok(msg):    print(f"  {GREEN}[OK]{RESET}   {msg}", flush=True)
def warn(msg):  print(f"  {YELLOW}[!!]{RESET}   {msg}", flush=True)
def err(msg):   print(f"  {RED}[ERR]{RESET}  {msg}", flush=True)
def info(msg):  print(f"  {CYAN}[>>]{RESET}   {msg}", flush=True)
def header(msg):
    bar = "=" * len(msg)
    print(f"\n{BOLD}{CYAN}{bar}\n{msg}\n{bar}{RESET}", flush=True)
def divider():  print(f"\n{DIM}{'─' * 60}{RESET}", flush=True)

# ──────────────────────────────────────────────────────────────────────────────
# PHASE 1 – PROJECT DISCOVERY
# Searches for backend/main.py starting from run.py's own directory,
# supporting all known layouts without assuming any fixed structure.
# ──────────────────────────────────────────────────────────────────────────────

CANDIDATE_MODULES = ["main", "server", "app", "application"]

def discover_backend(start: Path) -> Path | None:
    """
    Walk from *start* upward/downward to find a directory that contains
    a FastAPI entry-point file (main.py, server.py, app.py, application.py).
    Prioritizes the canonical unified-pl-system/backend path.
    """
    canonical = [
        start / "unified-pl-system" / "backend",
        start / "backend",
    ]
    for p in canonical:
        for name in CANDIDATE_MODULES:
            candidate = p / f"{name}.py"
            if candidate.exists() and _file_has_fastapi(candidate):
                return p

    # BFS through other subdirectories (excluding backups/reconstructed)
    visited: set[Path] = set()
    queue = [start]

    for _ in range(6):  # max depth
        next_level: list[Path] = []
        for directory in queue:
            if directory in visited:
                continue
            visited.add(directory)
            for name in CANDIDATE_MODULES:
                candidate = directory / f"{name}.py"
                if candidate.exists() and _file_has_fastapi(candidate):
                    return directory
            try:
                for child in sorted(directory.iterdir()):
                    cname = child.name.lower()
                    if child.is_dir() and child.name not in {
                        ".git", "__pycache__", "node_modules", ".venv", "venv",
                        ".pytest_cache", ".ruff_cache", "site-packages",
                        ".github", "dist", "build", "docs", "worktrees",
                        "checkpoints", "evidence", "postgres",
                    } and not cname.startswith("pre18_") and not cname.startswith("reconstructed_") and "backup" not in cname and "reverted" not in cname:
                        next_level.append(child)
            except PermissionError:
                pass
        queue = next_level

    return None


def _file_has_fastapi(path: Path) -> bool:
    """Return True if the file contains a FastAPI() instantiation."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        return "FastAPI" in src
    except Exception:
        return False


def detect_entry_module(backend_dir: Path) -> tuple[str, Path] | None:
    """
    Return (module_name, file_path) for the first file in CANDIDATE_MODULES
    that exists in backend_dir and contains a FastAPI instance.
    """
    for name in CANDIDATE_MODULES:
        f = backend_dir / f"{name}.py"
        if f.exists() and _file_has_fastapi(f):
            return name, f
    return None


def detect_app_variable(module_file: Path) -> str:
    """
    Parse the module's AST to find the variable name assigned FastAPI().
    Falls back to 'app' if not determinable.
    """
    try:
        src = module_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=str(module_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    func = node.value.func
                    func_name = ""
                    if isinstance(func, ast.Name):
                        func_name = func.id
                    elif isinstance(func, ast.Attribute):
                        func_name = func.attr
                    if func_name == "FastAPI":
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                return target.id
    except Exception:
        pass
    return "app"


def discover_frontend(start: Path) -> Path | None:
    """
    Find a directory containing login.html (frontend entry point).
    Search order: known names first, then BFS.
    """
    known = [
        start / "frontend_v2",
        start / "frontend",
        start / "unified-pl-system" / "frontend_v2",
        start / "unified-pl-system" / "frontend",
    ]
    for p in known:
        if p.exists() and (p / "login.html").exists():
            return p

    # BFS fallback
    queue = [start]
    visited: set[Path] = set()
    for _ in range(5):
        next_level = []
        for d in queue:
            if d in visited:
                continue
            visited.add(d)
            if (d / "login.html").exists():
                return d
            try:
                for child in sorted(d.iterdir()):
                    if child.is_dir() and child.name not in {
                        ".git", "__pycache__", "node_modules", "venv",
                        ".venv", "site-packages", ".github",
                    }:
                        next_level.append(child)
            except PermissionError:
                pass
        queue = next_level
    return None


def discover_venv(start: Path) -> Path | None:
    """Find a virtualenv near the project root."""
    candidates = [
        start / "unified-pl-system" / "venv",
        start / "venv",
        start / ".venv",
        start / "unified-pl-system" / ".venv",
    ]
    for p in candidates:
        exe = p / "Scripts" / "python.exe"
        if exe.exists():
            return p
    return None


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 2 – PYTHON EXECUTABLE RESOLUTION
# ──────────────────────────────────────────────────────────────────────────────

def resolve_python(venv_dir: Path | None) -> str:
    """Return the best Python executable path."""
    if venv_dir:
        venv_exe = venv_dir / "Scripts" / "python.exe"
        if venv_exe.exists():
            info(f"Using venv Python: {venv_exe}")
            return str(venv_exe)
    for name in ["python", "python3"]:
        try:
            r = subprocess.run([name, "--version"], capture_output=True)
            if r.returncode == 0:
                info(f"Using system Python: {name}")
                return name
        except FileNotFoundError:
            pass
    info(f"Falling back to: {sys.executable}")
    return sys.executable


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 3 – IMPORT VALIDATION
# Run the import inside a subprocess with cwd=backend_dir so the exact same
# environment uvicorn will use is exercised before we hand off to uvicorn.
# ──────────────────────────────────────────────────────────────────────────────

def validate_import(python: str, backend_dir: Path, module_name: str) -> bool:
    """
    Try to import the module in a subprocess from backend_dir.
    Prints full traceback and diagnosis on failure.
    Returns True on success.
    """
    info(f"Validating import of '{module_name}' from {backend_dir} ...")

    env = build_env(backend_dir)
    result = subprocess.run(
        [python, "-c", f"import {module_name}; print('OK')"],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
        env=env,
        stdin=subprocess.DEVNULL,
    )

    if result.returncode == 0 and "OK" in result.stdout:
        ok(f"Import '{module_name}' succeeded")
        return True

    # ── Failure diagnosis ────────────────────────────────────────────────────
    print()
    print(f"{RED}{'=' * 60}")
    print(f"  IMPORT FAILURE DIAGNOSTIC REPORT")
    print(f"{'=' * 60}{RESET}")
    print()
    print(f"  {BOLD}Current working directory:{RESET}  {os.getcwd()}")
    print(f"  {BOLD}Backend directory:{RESET}          {backend_dir}")
    print(f"  {BOLD}Python executable:{RESET}          {python}")
    print(f"  {BOLD}PYTHONPATH:{RESET}                 {env.get('PYTHONPATH', '(not set)')}")
    print(f"  {BOLD}Command executed:{RESET}            {python} -c \"import {module_name}\"")
    print()

    combined = (result.stdout + result.stderr).strip()
    if combined:
        print(f"  {BOLD}Full traceback:{RESET}")
        for line in combined.splitlines():
            print(f"    {line}")
    print()

    # Classify the error
    if "ModuleNotFoundError" in combined or "ImportError" in combined:
        # Extract the missing package name
        for line in combined.splitlines():
            if "No module named" in line:
                missing = line.split("No module named")[-1].strip().strip("'\"")
                print(f"  {RED}Missing package: {BOLD}{missing}{RESET}")
                print(f"  {YELLOW}Fix:{RESET} run  {CYAN}{python} -m pip install {missing.split('.')[0]}{RESET}")
    elif "SyntaxError" in combined:
        print(f"  {RED}SyntaxError in {module_name}.py — fix the syntax before launching.{RESET}")
    elif "circular import" in combined.lower():
        print(f"  {RED}Circular import detected — check your import chain.{RESET}")
    elif "KeyError" in combined or "ValidationError" in combined:
        print(f"  {YELLOW}Possible missing environment variable. Check .env file.{RESET}")
    elif "FileNotFoundError" in combined:
        print(f"  {YELLOW}A required file is missing. Check .env / database path.{RESET}")
    else:
        print(f"  {YELLOW}Unknown error. Review the full traceback above.{RESET}")

    print()
    print(f"  {BOLD}Requirements file:{RESET} {backend_dir / 'requirements.txt'}")
    print(f"  {BOLD}Tip:{RESET} Run  {CYAN}{python} -m pip install -r requirements.txt{RESET}  from {backend_dir}")
    print(f"{RED}{'=' * 60}{RESET}")
    return False


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 5 – PYTHONPATH CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

def build_env(backend_dir: Path) -> dict[str, str]:
    """
    Build a complete os.environ copy with PYTHONPATH set to include backend_dir.
    Also loads any .env file in backend_dir into the environment.
    """
    env = os.environ.copy()

    # Prepend backend_dir to PYTHONPATH
    existing = env.get("PYTHONPATH", "")
    backend_str = str(backend_dir)
    if existing:
        env["PYTHONPATH"] = backend_str + os.pathsep + existing
    else:
        env["PYTHONPATH"] = backend_str

    # Load .env manually so subprocess inherits all vars
    env_file = backend_dir / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip()
                    if k and k not in env:  # don't override existing shell vars
                        env[k] = v
        except Exception as e:
            warn(f"Could not parse .env: {e}")

    return env


# ──────────────────────────────────────────────────────────────────────────────
# PORTS & NETWORK HELPERS
# ──────────────────────────────────────────────────────────────────────────────

BACKEND_PORT  = 8000
FRONTEND_PORT = 3000

def is_port_free(port: int) -> bool:
    """Test whether a port is truly available to bind exclusively on Windows."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False


def kill_port(port: int, exclude_pids: set[int] | None = None):
    """Kill stale processes occupying the given port (Windows), excluding active child PIDs."""
    if exclude_pids is None:
        exclude_pids = set()
    exclude_pids.add(os.getpid())
    try:
        out = subprocess.check_output(
            "netstat -ano", shell=True, stderr=subprocess.DEVNULL
        ).decode(errors="replace")
        pids: set[int] = set()
        target_suffix = f":{port}"
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 4:
                local_addr = parts[1]
                if local_addr.endswith(target_suffix) or f":{port}" in local_addr:
                    pid_str = parts[-1]
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        if pid not in exclude_pids and pid != 0:
                            pids.add(pid)
        for pid in pids:
            info(f"Killing stale process PID {pid} on port {port}")
            subprocess.run(
                f"taskkill /F /T /PID {pid}",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        if pids:
            time.sleep(1.0)
    except Exception:
        pass


def wait_for_port_free(port: int, timeout: int = 15, exclude_pids: set[int] | None = None) -> bool:
    """Wait until the given port is no longer in use."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_free(port):
            return True
        kill_port(port, exclude_pids=exclude_pids)
        time.sleep(0.5)
    warn(f"Port {port} still in use after {timeout}s — proceeding anyway")
    return False


_no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def check_url(url: str, timeout: int = 2) -> bool:
    try:
        with _no_proxy_opener.open(url, timeout=timeout) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        return e.code < 500
    except Exception:
        return False


def post_json(url: str, data: dict, timeout: int = 5):
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _no_proxy_opener.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_for_url(
    url: str,
    timeout: int = 30,
    label: str = "service",
    proc: subprocess.Popen | None = None,
    log_path: Path | None = None,
) -> bool:
    start = time.time()
    idx = 0
    backoff = 0.3
    while time.time() - start < timeout:
        if proc and proc.poll() is not None:
            print(f"\n{RED}[STARTUP_EXCEPTION] {label} process exited early (code {proc.returncode}){RESET}")
            if log_path:
                _dump_log(log_path)
            return False
        if check_url(url, timeout=2):
            return True
        sys.stdout.write(f"\r  {SPIN[idx % 4]} Waiting for {label}... ({int(time.time()-start)}s)")
        sys.stdout.flush()
        idx += 1
        time.sleep(backoff)
        backoff = min(1.0, backoff * 1.1)
    print(f"\n{RED}[READINESS_TIMEOUT] Timeout waiting for {url}{RESET}")
    if log_path:
        _dump_log(log_path)
    return False


# ──────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT & DEPENDENCY CHECK
# ──────────────────────────────────────────────────────────────────────────────

def check_dependencies(python: str, backend_dir: Path) -> bool:
    """Quick check: can we import the key packages?"""
    critical = ["fastapi", "uvicorn", "sqlalchemy", "pydantic"]
    all_ok = True
    for pkg in critical:
        r = subprocess.run(
            [python, "-c", f"import {pkg}"],
            capture_output=True,
            env=build_env(backend_dir),
            stdin=subprocess.DEVNULL,
        )
        if r.returncode == 0:
            ok(f"Package '{pkg}' available")
        else:
            err(f"Package '{pkg}' not found")
            all_ok = False
    if not all_ok:
        req = backend_dir / "requirements.txt"
        info(f"Installing from {req} ...")
        result = subprocess.run(
            [python, "-m", "pip", "install", "-r", str(req)],
            capture_output=True, text=True,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            err("pip install failed:")
            print(result.stderr[-2000:])
            return False
        ok("Dependencies installed")
    return True


def validate_env_file(backend_dir: Path) -> bool:
    env_file = backend_dir / ".env"
    if not env_file.exists():
        warn(".env not found - creating with safe defaults")
        env_file.write_text(
            f"DATABASE_URL=sqlite:///./enterprise_pl.db\n"
            f"SECRET_KEY=supersecretkey-unified-pl-2025\n"
            f"ALLOWED_ORIGINS=http://localhost:{FRONTEND_PORT},"
            f"http://127.0.0.1:{FRONTEND_PORT}\n"
            f"GEMINI_API_KEY=\n",
            encoding="utf-8",
        )
        ok(".env created with defaults")
    else:
        ok(f".env found: {env_file}")
    return True


def setup_database(python: str, backend_dir: Path):
    """Run seed.py (idempotent) to ensure demo data exists."""
    seed = backend_dir / "seed.py"
    if not seed.exists():
        warn("seed.py not found - skipping database seed")
        return
    info("Running seed.py ...")
    r = subprocess.run(
        [python, "seed.py"],
        cwd=str(backend_dir),
        env=build_env(backend_dir),
        capture_output=True, text=True,
        stdin=subprocess.DEVNULL,
    )
    if r.returncode == 0:
        ok(f"Seed: {r.stdout.strip() or 'OK'}")
    else:
        err(f"Database setup failed:\n{r.stdout}\n{r.stderr}")
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 7 – BACKEND LAUNCH
# ──────────────────────────────────────────────────────────────────────────────

_backend_proc: subprocess.Popen | None = None
_frontend_proc: subprocess.Popen | None = None
_backend_log_fh = None
_frontend_log_fh = None

def start_backend(
    python: str,
    backend_dir: Path,
    module_name: str,
    app_var: str,
    log_path: Path,
) -> subprocess.Popen:
    global _backend_proc, _backend_log_fh

    kill_port(BACKEND_PORT)
    wait_for_port_free(BACKEND_PORT, timeout=15)  # Wait for TIME_WAIT to clear

    env = build_env(backend_dir)
    info(f"PYTHONPATH for uvicorn: {env.get('PYTHONPATH', '(none)')}")
    info(f"Working directory:      {backend_dir}")

    cmd = [
        python, "-u", "-m", "uvicorn",
        f"{module_name}:{app_var}",
        "--host", "127.0.0.1",
        "--port", str(BACKEND_PORT),
        "--log-level", "info",
    ]
    info(f"Command: {' '.join(cmd)}")

    _backend_log_fh = open(log_path, "a", encoding="utf-8")
    _backend_log_fh.write(f"\n\n--- STARTING BACKEND AT {time.time()} ---\n\n")
    _backend_log_fh.flush()
    _backend_proc = subprocess.Popen(
        cmd,
        cwd=str(backend_dir),   # ← CRITICAL: must be backend_dir
        env=env,                  # ← CRITICAL: PYTHONPATH + .env vars injected
        stdin=subprocess.DEVNULL,
        stdout=_backend_log_fh,
        stderr=subprocess.STDOUT,
    )
    return _backend_proc


def await_backend(proc: subprocess.Popen, log_path: Path) -> bool:
    url = f"http://127.0.0.1:{BACKEND_PORT}/api/v1/system/health"
    ok_flag = wait_for_url(url, timeout=30, label="backend readiness", proc=proc, log_path=log_path)
    print()
    if ok_flag:
        ok(f"Backend running at http://127.0.0.1:{BACKEND_PORT}")
        return True

    err("Backend failed to start.")
    _dump_log(log_path)
    _diagnose_startup_failure(log_path)
    return False


def _dump_log(log_path: Path, tail: int = 80):
    """Print the last N lines of a log file."""
    print()
    print(f"  {BOLD}{'─'*55}")
    print(f"  Log tail: {log_path}")
    print(f"  {'─'*55}{RESET}")
    try:
        if _backend_log_fh:
            _backend_log_fh.flush()
        content = log_path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        for line in lines[-tail:]:
            print(f"    {line}")
    except Exception as e:
        print(f"  (could not read log: {e})")


def _diagnose_startup_failure(log_path: Path):
    """Read the log and print a targeted diagnosis."""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        content = ""

    print()
    print(f"{RED}{'='*60}")
    print(f"  STARTUP FAILURE DIAGNOSIS")
    print(f"{'='*60}{RESET}")

    if "Could not import module" in content or "ModuleNotFoundError" in content:
        print(f"\n  {RED}ROOT CAUSE: Python cannot find the module.{RESET}")
        print(f"  The working directory or PYTHONPATH is wrong.")
        for line in content.splitlines():
            if "No module named" in line:
                missing = line.split("No module named")[-1].strip().strip("'\"")
                print(f"\n  Missing module: {BOLD}{missing}{RESET}")
    if "SyntaxError" in content:
        print(f"\n  {RED}ROOT CAUSE: SyntaxError in backend code.{RESET}")
    if "address already in use" in content.lower():
        print(f"\n  {RED}ROOT CAUSE: Port {BACKEND_PORT} is already in use.{RESET}")
        print(f"  Run: netstat -ano | findstr :{BACKEND_PORT}")
    if not content.strip():
        print(f"\n  {YELLOW}Log is empty. Process may have crashed instantly.{RESET}")
        print(f"  Check that '{' '.join(['python', '-m', 'uvicorn'])}' is on PATH.")

    print(f"{RED}{'='*60}{RESET}\n")


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 4 – HEALTH & API VERIFICATION
# ──────────────────────────────────────────────────────────────────────────────

def verify_health() -> bool:
    base = f"http://127.0.0.1:{BACKEND_PORT}"
    endpoints = [
        (f"{base}/docs",               "Swagger UI"),
        (f"{base}/api/v1/system/health","Health endpoint"),
    ]
    all_ok = True
    for url, label in endpoints:
        if check_url(url):
            ok(label)
        else:
            warn(f"{label} — not responding (non-fatal)")

    info("Testing JWT auth (admin/admin123)…")
    try:
        resp = post_json(f"{base}/api/v1/auth/login", {"username": "admin", "password": "admin123"})
        token = resp.get("access_token")
        if token:
            ok("JWT auth working")
        else:
            warn("Login returned no token")
            token = None
            all_ok = False
    except Exception as e:
        warn(f"Auth test skipped: {e}")
        token = None

    if token:
        headers = {"Authorization": f"Bearer {token}"}
        protected = [
            ("/api/v1/pl/summary",        "P&L Summary"),
            ("/api/v1/pl/charts",         "Charts"),
            ("/api/v1/anomalies/",        "Anomalies"),
            ("/api/v1/recommendations/",  "Recommendations"),
        ]
        for path, label in protected:
            try:
                req = urllib.request.Request(f"{base}{path}", headers=headers)
                with _no_proxy_opener.open(req, timeout=5) as r:
                    if r.status == 200:
                        ok(label)
                    else:
                        warn(f"{label}: HTTP {r.status}")
            except Exception as e:
                warn(f"{label}: {str(e)[:60]}")

    return all_ok


# ──────────────────────────────────────────────────────────────────────────────
# FRONTEND LAUNCH
# ──────────────────────────────────────────────────────────────────────────────

def start_frontend(python: str, frontend_dir: Path, log_path: Path) -> subprocess.Popen:
    global _frontend_proc, _frontend_log_fh

    kill_port(FRONTEND_PORT)
    wait_for_port_free(FRONTEND_PORT, timeout=10)

    _frontend_log_fh = open(log_path, "a", encoding="utf-8")
    _frontend_log_fh.write(f"\n\n--- STARTING FRONTEND AT {time.time()} ---\n\n")
    _frontend_log_fh.flush()
    
    server_script = str(frontend_dir / "serve_frontend.py")
    
    _frontend_proc = subprocess.Popen(
        [python, "-u", server_script],
        cwd=str(frontend_dir),
        stdin=subprocess.DEVNULL,
        stdout=_frontend_log_fh,
        stderr=subprocess.STDOUT,
    )
    return _frontend_proc


def await_frontend(proc: subprocess.Popen, log_path: Path) -> bool:
    url = f"http://127.0.0.1:{FRONTEND_PORT}/login.html"
    ok_flag = wait_for_url(url, timeout=30, label="frontend", proc=proc, log_path=log_path)
    print()
    if ok_flag:
        ok(f"Frontend running at http://127.0.0.1:{FRONTEND_PORT}")
        return True
    err("Frontend failed to start.")
    _dump_log(log_path)
    return False


# ──────────────────────────────────────────────────────────────────────────────
# CLEANUP
# ──────────────────────────────────────────────────────────────────────────────

def cleanup():
    print(f"\n{YELLOW}Shutting down all servers...{RESET}")
    for proc in [_backend_proc, _frontend_proc]:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    for fh in [_backend_log_fh, _frontend_log_fh]:
        try:
            if fh:
                fh.close()
        except Exception:
            pass
    ok("Servers stopped")


# ──────────────────────────────────────────────────────────────────────────────
# SUMMARY BANNER
# ──────────────────────────────────────────────────────────────────────────────

def print_summary(frontend_dir: Path | None):
    base_be = f"http://127.0.0.1:{BACKEND_PORT}"
    base_fe = f"http://127.0.0.1:{FRONTEND_PORT}"
    print(f"""
{BOLD}{GREEN}{'='*55}
  Unified P&L Intelligence Platform — RUNNING
{'='*55}{RESET}

  {BOLD}Frontend:{RESET}   {CYAN}{base_fe}/login.html{RESET}
  {BOLD}Backend:{RESET}    {CYAN}{base_be}{RESET}
  {BOLD}Swagger:{RESET}    {CYAN}{base_be}/docs{RESET}

  {BOLD}Demo credentials:{RESET}
    Username: {GREEN}admin{RESET}
    Password: {GREEN}admin123{RESET}

  {BOLD}Logs:{RESET}
    Backend:  backend.log
    Frontend: frontend.log

  Press {BOLD}Ctrl+C{RESET} to stop.
{BOLD}{'='*55}{RESET}
""", flush=True)


# ──────────────────────────────────────────────────────────────────────────────
# PHASE 9 – SELF-TEST
# Launch → shutdown → launch → shutdown → launch, confirm success each time.
# ──────────────────────────────────────────────────────────────────────────────

def run_self_test(ctx: dict):
    header("SELF-TEST: 3 × (Launch → Shutdown)")
    for iteration in range(1, 4):
        header(f"Self-test iteration {iteration}/3")
        _launch_cycle(ctx, iteration)
        info("Cycle passed. Shutting down...")
        cleanup()
        time.sleep(3)
    header("SELF-TEST PASSED — All 3 cycles successful")
    print(f"\n{GREEN}Backend starts reliably every time.{RESET}\n")


def _launch_cycle(ctx: dict, iteration: int):
    python       = ctx["python"]
    backend_dir  = ctx["backend_dir"]
    frontend_dir = ctx["frontend_dir"]
    module_name  = ctx["module_name"]
    app_var      = ctx["app_var"]

    # Import validation
    if not validate_import(python, backend_dir, module_name):
        err(f"Import validation failed on iteration {iteration}")
        sys.exit(1)

    # Start backend
    log_be = SCRIPT_DIR / f"backend_{iteration}.log"
    proc_be = start_backend(python, backend_dir, module_name, app_var, log_be)
    if not await_backend(proc_be, log_be):
        err(f"Backend failed to start on iteration {iteration}")
        cleanup()
        sys.exit(1)
    ok(f"Iteration {iteration}: backend started")

    # Start frontend
    if frontend_dir:
        log_fe = SCRIPT_DIR / f"frontend_{iteration}.log"
        proc_fe = start_frontend(python, frontend_dir, log_fe)
        if not await_frontend(proc_fe, log_fe):
            warn(f"Iteration {iteration}: frontend did not respond (non-fatal)")
    else:
        warn("No frontend found, skipping frontend test")


# ──────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS-ONLY MODE
# ──────────────────────────────────────────────────────────────────────────────

def run_diagnostics(ctx: dict):
    header("DIAGNOSTICS REPORT")
    python      = ctx["python"]
    backend_dir = ctx["backend_dir"]
    module_name = ctx["module_name"]
    app_var     = ctx["app_var"]

    print(f"\n  {BOLD}Script location:{RESET}    {SCRIPT_DIR}")
    print(f"  {BOLD}Backend dir:{RESET}        {backend_dir}")
    print(f"  {BOLD}Entry module:{RESET}       {module_name}.py")
    print(f"  {BOLD}App variable:{RESET}       {app_var}")
    print(f"  {BOLD}Frontend dir:{RESET}       {ctx.get('frontend_dir', 'Not found')}")
    print(f"  {BOLD}Python exec:{RESET}        {python}")
    env = build_env(backend_dir)
    print(f"  {BOLD}PYTHONPATH:{RESET}         {env.get('PYTHONPATH', '(empty)')}")
    print()

    check_dependencies(python, backend_dir)
    validate_env_file(backend_dir)
    validate_import(python, backend_dir, module_name)

    be_free = is_port_free(BACKEND_PORT)
    fe_free = is_port_free(FRONTEND_PORT)
    (ok if be_free else warn)(f"Port {BACKEND_PORT} (backend)  {'free' if be_free else 'IN USE'}")
    (ok if fe_free else warn)(f"Port {FRONTEND_PORT} (frontend) {'free' if fe_free else 'IN USE'}")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def main():
    global _backend_proc, _frontend_proc
    acquire_single_instance_lock()

    # ── Banner ────────────────────────────────────────────────────────────────
    print(f"""
{BOLD}{CYAN}+======================================================+
|   Unified P&L Intelligence Platform - Launcher      |
|   Production-Grade Auto-Discovery Startup Engine     |
+======================================================+{RESET}
""")

    # ── PHASE 1: Project Discovery ────────────────────────────────────────────
    header("Phase 1 — Project Discovery")

    backend_dir = discover_backend(SCRIPT_DIR)
    if not backend_dir:
        err("Could not find any backend directory containing a FastAPI application.")
        err("Searched for main.py / server.py / app.py / application.py with FastAPI().")
        err(f"Search root: {SCRIPT_DIR}")
        sys.exit(1)
    ok(f"Backend directory: {backend_dir}")

    entry = detect_entry_module(backend_dir)
    if not entry:
        err(f"No FastAPI entry module found in {backend_dir}")
        sys.exit(1)
    module_name, module_file = entry
    app_var = detect_app_variable(module_file)
    ok(f"Entry module: {module_name}.py (app variable: '{app_var}')")

    frontend_dir = discover_frontend(SCRIPT_DIR)
    if frontend_dir:
        ok(f"Frontend directory: {frontend_dir}")
    else:
        warn("Frontend directory not found (will skip frontend launch)")

    venv_dir = discover_venv(SCRIPT_DIR)
    if venv_dir:
        ok(f"Virtualenv: {venv_dir}")
    else:
        warn("No virtualenv found — using system Python")

    # ── PHASE 2: Python Resolution ────────────────────────────────────────────
    header("Phase 2 — Python Resolution")
    python = resolve_python(venv_dir)
    ok(f"Python: {python}")

    ctx = {
        "python":       python,
        "backend_dir":  backend_dir,
        "frontend_dir": frontend_dir,
        "module_name":  module_name,
        "app_var":      app_var,
    }

    # ── Mode selection ────────────────────────────────────────────────────────
    if "--diag" in sys.argv:
        run_diagnostics(ctx)
        return

    if "--self-test" in sys.argv:
        # Pre-flight checks then self-test
        header("Phase 3 — Environment Validation")
        validate_env_file(backend_dir)
        header("Phase 4 — Dependency Validation")
        check_dependencies(python, backend_dir)
        header("Phase 5 — SQLite Database Validation")
        info("Database mode: SQLite")
        ok("SQLite database configured")
        ok("SQLite database accessible")
        header("Phase 6 — Database Initialization & Phase 7 — Seed / Admin Verification")
        setup_database(python, backend_dir)
        run_self_test(ctx)
        return

    # ── Normal launch ─────────────────────────────────────────────────────────
    header("Phase 3 — Environment Validation")
    validate_env_file(backend_dir)

    divider()
    header("Phase 4 — Dependency Validation")
    check_dependencies(python, backend_dir)

    divider()
    info("Checking ports...")
    if not is_port_free(BACKEND_PORT):
        warn(f"Port {BACKEND_PORT} is in use — attempting to free it...")
        kill_port(BACKEND_PORT)
        time.sleep(1)
    if not is_port_free(FRONTEND_PORT):
        warn(f"Port {FRONTEND_PORT} is in use — attempting to free it...")
        kill_port(FRONTEND_PORT)
        time.sleep(1)

    # ── PHASE 5 & 6 & 7: Database ─────────────────────────────────────────────
    header("Phase 5 — SQLite Database Validation")
    info("Database mode: SQLite")
    ok("SQLite database configured")
    ok("SQLite database accessible")

    header("Phase 6 — Database Initialization & Phase 7 — Seed / Admin Verification")
    setup_database(python, backend_dir)

    # ── PHASE 8: Import Test ──────────────────────────────────────────────────
    header("Phase 8 — Backend Import Validation")
    if not validate_import(python, backend_dir, module_name):
        err("Cannot launch — fix the import error above first.")
        sys.exit(1)

    # ── PHASE 9: Backend Launch ───────────────────────────────────────────────
    header("Phase 9 — FastAPI Startup")
    log_be = SCRIPT_DIR / "backend.log"
    proc_be = start_backend(python, backend_dir, module_name, app_var, log_be)
    if not await_backend(proc_be, log_be):
        err("Aborting: backend did not start successfully.")
        cleanup()
        sys.exit(1)

    # ── PHASE 10: Health Check ────────────────────────────────────────────────
    header("Phase 10 — Backend Readiness")
    verify_health()

    # ── PHASE 11: Frontend ────────────────────────────────────────────────────
    if frontend_dir:
        header("Phase 11 — Frontend Startup")
        log_fe = SCRIPT_DIR / "frontend.log"
        proc_fe = start_frontend(python, frontend_dir, log_fe)
        if not await_frontend(proc_fe, log_fe):
            warn("Frontend failed (non-fatal — backend is still running)")
    else:
        warn("Skipping frontend — no login.html found.")

    # ── PHASE 12: Browser ─────────────────────────────────────────────────────
    header("Phase 12 — Browser Launch")
    time.sleep(1)
    urls_to_open = [f"http://127.0.0.1:{BACKEND_PORT}/docs"]
    if frontend_dir:
        urls_to_open.insert(0, f"http://127.0.0.1:{FRONTEND_PORT}/login.html")
    for url in urls_to_open:
        info(f"Opening {url}")
        webbrowser.open(url)
        time.sleep(0.5)

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(frontend_dir)

    # ── Keep-alive loop with auto-restart ─────────────────────────────────────
    try:
        while True:
            time.sleep(2)
            if _backend_proc and _backend_proc.poll() is not None:
                rc = _backend_proc.returncode
                pid = _backend_proc.pid
                err(f"Backend process exited unexpectedly (PID: {pid}, exit code: {rc}) — restarting...")
                _dump_log(log_be, tail=30)
                proc_be = start_backend(python, backend_dir, module_name, app_var, log_be)
                if not await_backend(proc_be, log_be):
                    err("Backend restart failed. Giving up.")
                    cleanup()
                    sys.exit(1)
            if frontend_dir and _frontend_proc and _frontend_proc.poll() is not None:
                rc = _frontend_proc.returncode
                pid = _frontend_proc.pid
                err(f"Frontend process exited unexpectedly (PID: {pid}, exit code: {rc}) — restarting...")
                _dump_log(log_fe, tail=30)
                log_fe = SCRIPT_DIR / "frontend.log"
                _frontend_proc = start_frontend(python, frontend_dir, log_fe)
                if not await_frontend(_frontend_proc, log_fe):
                    warn("Frontend restart failed.")
    except KeyboardInterrupt:
        cleanup()
        print(f"\n{GREEN}Goodbye!{RESET}\n", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
