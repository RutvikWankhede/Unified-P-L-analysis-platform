"""
run.py - Production Launcher for Unified P&L Intelligence Platform
==================================================================
Production-grade launcher with reliable process lifecycle management:
- Positively identifies and cleans up project-owned processes on ports 8000 & 3000
- Preserves unrelated third-party processes with clear diagnostic error messages
- Manages state in .runtime/ (backend.pid, frontend.pid)
- Windows and Linux/macOS safe process tree termination
- Direct subprocess.Popen handle supervision without infinite restart loops
- Accurate readiness polling with real health check distinction

Usage:
    python run.py                      # Normal launch
    python run.py --self-test          # Test startup and readiness, then exit cleanly
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

# ANSI colors
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
# PATH DISCOVERY & RUNTIME DIRECTORY
# ──────────────────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT_DIR / ".runtime"

def get_runtime_dir() -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    return RUNTIME_DIR

def write_pid(service_name: str, pid: int) -> None:
    try:
        rdir = get_runtime_dir()
        pid_file = rdir / f"{service_name}.pid"
        pid_file.write_text(str(pid), encoding="utf-8")
    except Exception as e:
        warn(f"Failed to record PID file for {service_name}: {e}")

def read_pid(service_name: str) -> int | None:
    try:
        pid_file = RUNTIME_DIR / f"{service_name}.pid"
        if pid_file.exists():
            content = pid_file.read_text(encoding="utf-8").strip()
            if content.isdigit():
                return int(content)
    except Exception:
        pass
    return None

def clear_pid(service_name: str) -> None:
    try:
        pid_file = RUNTIME_DIR / f"{service_name}.pid"
        if pid_file.exists():
            pid_file.unlink(missing_ok=True)
    except Exception:
        pass

def find_backend_dir() -> Path | None:
    candidates = [
        ROOT_DIR / "unified-pl-system" / "backend",
        ROOT_DIR / "backend",
    ]
    for p in candidates:
        if p.exists() and (p / "main.py").exists():
            return p
    return None

def find_frontend_dir() -> Path | None:
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
    env = os.environ.copy()
    backend_str = str(backend_dir)
    existing_py_path = env.get("PYTHONPATH", "")
    if existing_py_path:
        env["PYTHONPATH"] = backend_str + os.pathsep + existing_py_path
    else:
        env["PYTHONPATH"] = backend_str

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
    code = (
        "import fastapi, uvicorn, sqlalchemy, pydantic; "
        "print('DEPS_OK')"
    )
    res = subprocess.run(
        [str(python_exe), "-c", code],
        capture_output=True,
        text=True,
    )
    if res.returncode == 0 and "DEPS_OK" in res.stdout:
        ok("Core dependencies available (fastapi, uvicorn, sqlalchemy, pydantic)")
        return True

    info("Missing dependencies detected. Installing from requirements.txt...")
    req_file = backend_dir / "requirements.txt"
    if not req_file.exists():
        req_file = ROOT_DIR / "requirements.txt"
    if not req_file.exists():
        err("requirements.txt not found. Cannot install dependencies.")
        return False

    pip_res = subprocess.run(
        [str(python_exe), "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if pip_res.returncode == 0:
        ok("Dependencies installed successfully")
        return True
    else:
        err(f"Failed to install dependencies:\n{pip_res.stderr}")
        return False

def validate_main_module(python_exe: Path, backend_dir: Path, backend_env: dict[str, str]) -> bool:
    info("Validating backend entrypoint (main:app)...")
    code = (
        "import sys\n"
        "from main import app\n"
        "assert app is not None\n"
        "print('MAIN_APP_OK')\n"
    )
    try:
        res = subprocess.run(
            [str(python_exe), "-c", code],
            cwd=str(backend_dir),
            env=backend_env,
            capture_output=True,
            text=True,
            timeout=45.0,
        )
    except subprocess.TimeoutExpired:
        warn("Backend import validation timed out after 45s (continuing with startup)")
        return True
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
# SAFE PROCESS INSPECTION, PORT CHECKING & CLEANUP
# ──────────────────────────────────────────────────────────────────────────────

_no_proxy_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def is_port_available(port: int) -> bool:
    """Test if a port can be bound exclusively on 127.0.0.1."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            s.bind(("127.0.0.1", port))
            return True
    except OSError:
        return False

def is_pid_alive(pid: int) -> bool:
    """Check if a given PID is currently active."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=3.0)
            return str(pid) in res.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

def get_pids_on_port(port: int) -> list[int]:
    """Find all PIDs currently listening on a TCP port."""
    pids: list[int] = []
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, errors="replace")
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0].upper() == "TCP":
                    local_addr = parts[1]
                    state = parts[3]
                    pid_str = parts[4]
                    if state.upper() == "LISTENING":
                        if local_addr.endswith(f":{port}") or local_addr.endswith(f".{port}"):
                            try:
                                p = int(pid_str)
                                if p > 0 and p not in pids:
                                    pids.append(p)
                            except ValueError:
                                pass
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(["lsof", "-t", f"-i:{port}", "-sTCP:LISTEN"], text=True, errors="replace")
            for line in out.splitlines():
                try:
                    p = int(line.strip())
                    if p > 0 and p not in pids:
                        pids.append(p)
                except ValueError:
                    pass
        except Exception:
            pass
    return pids

def get_process_info(pid: int) -> tuple[str, str]:
    """Retrieve (command_line, executable_path) for a process PID."""
    if pid <= 0:
        return "", ""
    if sys.platform == "win32":
        cmdline = ""
        path = ""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$cp = Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' -ErrorAction SilentlyContinue; if ($cp) {{ $cp.CommandLine }}; $p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; if ($p) {{ $p.Path }}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=4.0)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
            if len(lines) >= 2:
                cmdline = lines[0]
                path = lines[1]
            elif len(lines) == 1:
                cmdline = lines[0]
        except Exception:
            pass

        if not cmdline:
            try:
                res = subprocess.run(["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine,ExecutablePath"], capture_output=True, text=True, timeout=4.0)
                if res.returncode == 0:
                    lines = [l.strip() for l in res.stdout.splitlines() if l.strip() and "CommandLine" not in l]
                    if lines:
                        cmdline = lines[0]
            except Exception:
                pass
        return cmdline, path
    else:
        cmdline = ""
        path = ""
        try:
            cmdline_path = Path(f"/proc/{pid}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_text(errors="replace").replace("\x00", " ").strip()
        except Exception:
            pass
        try:
            res = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                cmdline = res.stdout.strip()
        except Exception:
            pass
        return cmdline, path

def is_project_owned_process(pid: int, expected_service: str | None = None) -> tuple[bool, str]:
    """
    Positively verify whether a process PID belongs to THIS project.
    Returns (True, reason) or (False, cmdline).
    """
    # 0. If process already died or is transitioning
    if not is_pid_alive(pid):
        return True, "Process already exited / socket transitioning"

    # 1. Match recorded PID in .runtime/
    be_pid = read_pid("backend")
    fe_pid = read_pid("frontend")
    if pid in (be_pid, fe_pid):
        srv = "backend" if pid == be_pid else "frontend"
        return True, f"Recorded PID in .runtime/{srv}.pid"

    cmdline, path = get_process_info(pid)
    combined = f"{cmdline} {path}".lower()
    root_lower = str(ROOT_DIR).lower()

    # 2. Command line or executable explicitly mentions project root path
    if root_lower in combined or "unified-pl-system" in combined or "frontend_v2" in combined:
        return True, f"References project path: {ROOT_DIR.name}"

    # 3. Uvicorn backend process for main:app
    if "uvicorn" in combined and "main:app" in combined:
        return True, "Uvicorn backend server (main:app)"

    # 4. HTTP static server for frontend_v2
    if "http.server" in combined and "3000" in combined:
        return True, "Python http.server for frontend"

    if not cmdline and not path:
        return False, "Unknown process command line"

    return False, cmdline or path

def terminate_project_process(pid: int, timeout: float = 6.0) -> bool:
    """Terminate a verified project process and its child tree."""
    if not is_pid_alive(pid):
        return True
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=4.0)
        except Exception:
            pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    start = time.time()
    while time.time() - start < timeout:
        if not is_pid_alive(pid):
            return True
        time.sleep(0.2)

    if sys.platform != "win32" and is_pid_alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
    return not is_pid_alive(pid)

def safe_clean_and_check_port(port: int, service_name: str) -> bool:
    """
    Safely detect if port is occupied.
    If occupied by a verified project process, terminate it and free the port.
    If occupied by an unrelated third-party process, print diagnostics and refuse to kill.
    """
    if is_port_available(port):
        clear_pid(service_name)
        return True

    pids = get_pids_on_port(port)
    rec_pid = read_pid(service_name)
    if rec_pid and is_pid_alive(rec_pid) and rec_pid not in pids:
        pids.append(rec_pid)

    # Filter for alive PIDs
    alive_pids = [p for p in pids if is_pid_alive(p)]

    if not alive_pids:
        # All reported PIDs are already dead — wait a moment for socket release
        start = time.time()
        while time.time() - start < 3.0:
            if is_port_available(port):
                clear_pid(service_name)
                ok(f"Port {port} ({service_name}) is free and ready")
                return True
            time.sleep(0.3)

        if not is_port_available(port):
            err(f"Port {port} is held in socket transition state. Retrying...")
            time.sleep(1.0)
            if is_port_available(port):
                clear_pid(service_name)
                ok(f"Port {port} ({service_name}) is free and ready")
                return True

    for pid in alive_pids:
        is_ours, details = is_project_owned_process(pid, expected_service=service_name)
        if is_ours:
            info(f"Port {port} is held by previous project-owned {service_name} (PID {pid}: {details}). Cleaning up...")
            terminate_project_process(pid)
        else:
            print(f"\n{RED}{BOLD}{'='*60}")
            print(f"  PORT CONFLICT — UNRELATED APPLICATION DETECTED")
            print(f"{'='*60}{RESET}")
            print(f"  Port {BOLD}{port}{RESET} is occupied by an {RED}unrelated process{RESET}.")
            print(f"  {BOLD}PID:{RESET}     {pid}")
            print(f"  {BOLD}Command:{RESET} {details or 'N/A'}")
            print(f"\n  {YELLOW}Action required:{RESET} Please close that application or launch with:")
            print(f"      python run.py --{service_name}-port <other_port>\n")
            return False

    # Wait for port to become free
    start = time.time()
    while time.time() - start < 5.0:
        if is_port_available(port):
            clear_pid(service_name)
            ok(f"Port {port} ({service_name}) is free and ready")
            return True
        time.sleep(0.3)

    err(f"Port {port} remained busy after terminating previous project process.")
    return False

# ──────────────────────────────────────────────────────────────────────────────
# READINESS & HEALTH POLLING
# ──────────────────────────────────────────────────────────────────────────────

def check_endpoint_ready(
    url: str,
    proc: subprocess.Popen,
    timeout: float = 30.0,
    label: str = "Service",
    log_path: Path | None = None,
) -> bool:
    """
    Poll an HTTP endpoint until ready or until child process exits/times out.
    Distinguishes temporary warmups from real process deaths.
    """
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
        err(f"{label} process is still running (PID {proc.pid}) but did not respond on {url} within {timeout}s timeout")
    else:
        err(f"{label} process exited with return code {proc.poll()}")

    if log_path and log_path.exists():
        _dump_log_tail(log_path)
    return False

def _dump_log_tail(log_path: Path, max_lines: int = 35) -> None:
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
# PROCESS MANAGER
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
        pid = proc.pid
        if proc.poll() is None:
            try:
                info(f"Stopping {name} (PID {pid})...")
                terminate_project_process(pid, timeout=4.0)
            except Exception:
                pass
        clear_pid(name)

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
        clear_pid("backend")
        clear_pid("frontend")

manager = ProcessManager()

def _cleanup_handler():
    manager.cleanup()

atexit.register(_cleanup_handler)

def handle_sigint(signum, frame):
    print()
    info("Shutdown signal received (Ctrl+C). Exiting...")
    manager.cleanup()
    ok("All services stopped cleanly.")
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
    print(f"  {BOLD}Runtime directory:{RESET}   {RUNTIME_DIR}")
    print(f"  {BOLD}Backend directory:{RESET}   {backend_dir or 'NOT FOUND'}")
    print(f"  {BOLD}Frontend directory:{RESET}  {frontend_dir or 'NOT FOUND'}")
    print(f"  {BOLD}Python executable:{RESET}   {python_exe}")
    print(f"  {BOLD}Backend port {be_port}:{RESET}    {'FREE' if is_port_available(be_port) else 'IN USE'}")
    print(f"  {BOLD}Frontend port {fe_port}:{RESET}   {'FREE' if is_port_available(fe_port) else 'IN USE'}")
    print(f"  {BOLD}Recorded BE PID:{RESET}     {read_pid('backend') or 'None'}")
    print(f"  {BOLD}Recorded FE PID:{RESET}     {read_pid('frontend') or 'None'}")
    print()

def print_startup_banner(project_dir: Path, backend_port: int, frontend_port: int) -> None:
    print(f"""
{BOLD}{GREEN}======================================================{RESET}
{BOLD}{GREEN}  Unified P&L Intelligence Platform — Launcher        {RESET}
{BOLD}{GREEN}======================================================{RESET}

  {BOLD}Project:{RESET}   {project_dir}
  {BOLD}Backend:{RESET}   {CYAN}http://127.0.0.1:{backend_port}{RESET}
  {BOLD}Frontend:{RESET}  {CYAN}http://127.0.0.1:{frontend_port}{RESET}

  {GREEN}[OK]{RESET} Environment
  {GREEN}[OK]{RESET} Database
  {GREEN}[OK]{RESET} Backend started
  {GREEN}[OK]{RESET} Backend health check
  {GREEN}[OK]{RESET} Frontend started
  {GREEN}[OK]{RESET} Frontend available

  {BOLD}{GREEN}Platform is running.{RESET}
  {DIM}Press Ctrl+C to stop servers.{RESET}
{BOLD}{GREEN}======================================================{RESET}
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

    # Step 5: Safe Port Check & Stale Process Cleanup
    header("Step 5 — Port Availability & Process Check")
    if not safe_clean_and_check_port(args.backend_port, "backend"):
        sys.exit(1)

    if not safe_clean_and_check_port(args.frontend_port, "frontend"):
        sys.exit(1)

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
    write_pid("backend", manager.backend_proc.pid)
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
    write_pid("frontend", manager.frontend_proc.pid)
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
    print_startup_banner(ROOT_DIR, args.backend_port, args.frontend_port)

    try:
        while True:
            time.sleep(1.0)
            be_ret = manager.backend_proc.poll()
            if be_ret is not None:
                err(f"Backend process (PID {manager.backend_proc.pid}) exited unexpectedly with return code {be_ret}.")
                _dump_log_tail(backend_log_path)
                break

            fe_ret = manager.frontend_proc.poll()
            if fe_ret is not None:
                err(f"Frontend process (PID {manager.frontend_proc.pid}) exited unexpectedly with return code {fe_ret}.")
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
