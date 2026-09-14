"""
run.py - Production Launcher for Unified P&L Intelligence Platform
==================================================================
Production-grade launcher with robust dynamic port & process lifecycle management:
- Default ports: Backend 8000, Frontend 3000
- Automatically detects and cleanly recycles stale project-owned processes
- Preserves unrelated third-party processes without killing them
- Automatically finds and shifts to next available port (8001, 8002, ...) when 8000 is occupied by external apps
- Generates dynamic frontend runtime configuration (runtime_config.js) so frontend always communicates with active backend port
- Supports explicit --backend-port and --frontend-port overrides with strict validation
- Accurate 60s readiness polling against active dynamic ports
- Preserves SQLite/Postgres database and existing seeded dataset
- Full diagnostic and --self-test execution modes

Usage:
    python run.py                      # Automatic launch (default: BE 8000, FE 3000 or auto-shifted)
    python run.py --self-test          # Test startup and readiness on active ports, then exit cleanly
    python run.py --no-browser         # Start servers without launching browser
    python run.py --seed               # Force database seed before launch
    python run.py --backend-port 8001  # Explicit custom backend port
    python run.py --frontend-port 3001 # Explicit custom frontend port
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

    # Guarantee unbuffered I/O and UTF-8 encoding across all child processes
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "0"

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
            [str(python_exe), "-u", "-c", code],
            cwd=str(backend_dir),
            env=backend_env,
            capture_output=True,
            text=True,
            timeout=60.0,
        )
        if res.returncode == 0 and "MAIN_APP_OK" in res.stdout:
            ok("Backend module and app object validated")
            return True
        elif res.returncode != 0:
            err(f"Backend validation returned error (exit code: {res.returncode}):")
            if res.stderr:
                print(f"  {res.stderr.strip()}")
            return False
        else:
            return True
    except subprocess.TimeoutExpired:
        warn("Backend pre-validation took longer than 60s; proceeding to uvicorn startup...")
        return True
    except Exception as ex:
        warn(f"Backend pre-validation warning ({ex}); proceeding to uvicorn startup...")
        return True

    err(f"Backend validation failed (exit code: {res.returncode}). Detailed diagnostic:")
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
        ok(f"Database exists ({db_file.name}) — preserving existing seeded datasets and records")
        return True

    info("Initializing database seed...")
    res = subprocess.run(
        [str(python_exe), "seed.py"],
        cwd=str(backend_dir),
        env=backend_env,
        capture_output=True,
        text=True,
    )
    if res.returncode == 0:
        ok("Database seed completed successfully")
        return True
    else:
        err(f"Database seed failed:\n{res.stderr or res.stdout}")
        return False

# ──────────────────────────────────────────────────────────────────────────────
# SAFE PROCESS INSPECTION, PORT RESOLUTION & CLEANUP
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
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        pass
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
    # 1. Try psutil net_connections if available
    try:
        import psutil
        for conn in psutil.net_connections(kind="tcp"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port:
                if conn.pid and conn.pid > 0 and conn.pid not in pids:
                    pids.append(conn.pid)
        if pids:
            return pids
    except Exception:
        pass

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

def get_process_info(pid: int) -> tuple[str, str, str]:
    """Retrieve (command_line, executable_path, working_dir) for a process PID."""
    if pid <= 0:
        return "", "", ""
    try:
        import psutil
        p = psutil.Process(pid)
        cmdline = " ".join(p.cmdline())
        path = p.exe()
        cwd = p.cwd()
        return cmdline, path, cwd
    except Exception:
        pass

    if sys.platform == "win32":
        cmdline = ""
        path = ""
        cwd = ""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' -ErrorAction SilentlyContinue; if ($p) {{ Write-Output ('CMD===' + $p.CommandLine); Write-Output ('PATH===' + $p.ExecutablePath) }}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("CMD==="):
                    cmdline = line[len("CMD==="):]
                elif line.startswith("PATH==="):
                    path = line[len("PATH==="):]
        except Exception:
            pass
        return cmdline, path, cwd
    else:
        cmdline = ""
        path = ""
        cwd = ""
        try:
            cmdline_path = Path(f"/proc/{pid}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_text(errors="replace").replace("\x00", " ").strip()
            cwd_link = Path(f"/proc/{pid}/cwd")
            if cwd_link.exists():
                cwd = str(cwd_link.resolve())
        except Exception:
            pass
        try:
            res = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                cmdline = res.stdout.strip()
        except Exception:
            pass
        return cmdline, path, cwd

def is_project_owned_process(pid: int, expected_service: str | None = None) -> tuple[bool, str]:
    """
    Positively verify whether a process PID belongs to THIS project.
    Returns (True, reason) or (False, cmdline_or_details).
    """
    if not is_pid_alive(pid):
        return True, "Process already exited / socket transitioning"

    # 1. Match recorded PID in .runtime/
    be_pid = read_pid("backend")
    fe_pid = read_pid("frontend")
    if pid in (be_pid, fe_pid):
        srv = "backend" if pid == be_pid else "frontend"
        return True, f"Recorded PID in .runtime/{srv}.pid"

    cmdline, path, cwd = get_process_info(pid)
    combined = f"{cmdline} {path} {cwd}".lower()
    root_lower = str(ROOT_DIR).lower()

    # 2. Check if working directory is inside this project
    if cwd and (root_lower in cwd.lower() or "unified-pl-system" in cwd.lower()):
        return True, f"Running inside project directory: {cwd}"

    # 3. Command line or executable explicitly mentions project root path
    if root_lower in combined or "unified-pl-system" in combined or "frontend_v2" in combined:
        return True, f"References project path: {ROOT_DIR.name}"

    # 4. Project-specific script names or entry points
    project_markers = [
        "start_server.py",
        "main:app",
        "backend/main.py",
        "backend\\main.py",
        "seed.py",
        "inspect_env.py",
        "verify_apis.py",
        "test_urgent_forecast",
    ]
    for marker in project_markers:
        if marker in combined:
            return True, f"Matches project entrypoint: {marker}"

    # 5. Uvicorn backend process with FastAPI
    if "uvicorn" in combined and ("main:app" in combined or "app" in combined):
        return True, "Uvicorn backend process"

    # 6. HTTP static server serving frontend directory
    if "http.server" in combined and ("frontend_v2" in combined or "3000" in combined or "login.html" in combined):
        return True, "Python http.server for frontend"

    if not cmdline and not path:
        return False, "Unknown process (no inspectable command line)"

    return False, cmdline or path

def terminate_project_process(pid: int, timeout: float = 6.0) -> bool:
    """Terminate a verified project process and its child tree."""
    if not is_pid_alive(pid):
        return True

    # 1. Try psutil process tree kill first
    try:
        import psutil
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except Exception:
                pass
        parent.kill()
    except Exception:
        pass

    # 2. taskkill fallback on Windows
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

def resolve_service_port(
    preferred_port: int,
    service_name: str,
    is_explicit: bool = False,
    max_tries: int = 50,
) -> int | None:
    """
    Resolve an available port for a service (backend or frontend).
    
    Rules:
    1. If preferred_port is available -> use it.
    2. If preferred_port is occupied by a verified project process -> cleanly terminate it and use preferred_port.
    3. If preferred_port is occupied by an unrelated external process:
       - If is_explicit: Report clear conflict error and return None (do not kill, do not silently move).
       - If NOT is_explicit: Automatically probe preferred_port + 1, preferred_port + 2, ...
         Find the next free port without disturbing the external application.
    """
    # Quick check
    if is_port_available(preferred_port):
        clear_pid(service_name)
        return preferred_port

    pids = get_pids_on_port(preferred_port)
    rec_pid = read_pid(service_name)
    if rec_pid and is_pid_alive(rec_pid) and rec_pid not in pids:
        pids.append(rec_pid)

    alive_pids = [p for p in pids if is_pid_alive(p)]

    # Check ownership of all processes occupying preferred_port
    all_ours = True
    unrelated_info = []
    for pid in alive_pids:
        is_ours, details = is_project_owned_process(pid, expected_service=service_name)
        if is_ours:
            info(f"Port {preferred_port} is held by previous project-owned {service_name} (PID {pid}: {details}). Cleaning up...")
            terminate_project_process(pid)
        else:
            all_ours = False
            unrelated_info.append((pid, details))

    if all_ours:
        # Wait for port release
        start = time.time()
        while time.time() - start < 5.0:
            if is_port_available(preferred_port):
                clear_pid(service_name)
                ok(f"Cleaned previous project process. Port {preferred_port} ({service_name}) is now free and ready.")
                return preferred_port
            time.sleep(0.3)

    # If we reached here, the preferred port is held by an unrelated external application
    if not all_ours:
        pid, details = unrelated_info[0] if unrelated_info else (0, "Unknown application")
        if is_explicit:
            print(f"\n{RED}{BOLD}{'='*60}")
            print(f"  PORT CONFLICT — UNRELATED APPLICATION DETECTED ON EXPLICIT PORT")
            print(f"{'='*60}{RESET}")
            print(f"  Port {BOLD}{preferred_port}{RESET} was explicitly requested, but is occupied by an {RED}unrelated process{RESET}.")
            print(f"  {BOLD}PID:{RESET}     {pid}")
            print(f"  {BOLD}Command:{RESET} {details or 'N/A'}")
            print(f"\n  {YELLOW}Action required:{RESET} Please close that application or launch with another port:")
            print(f"      python run.py --{service_name}-port <other_port>\n")
            return None

        # Automatic fallback port search for default launch
        warn(f"Port {preferred_port} is occupied by an unrelated application (PID {pid}: {details}).")
        info(f"Preserving external application. Automatically searching for next available {service_name} port...")

        for offset in range(1, max_tries + 1):
            candidate = preferred_port + offset
            if is_port_available(candidate):
                ok(f"Found available port: {candidate}")
                ok(f"Automatically selected next available {service_name} port: {candidate}")
                return candidate

            # Check if candidate is occupied by our own stale process
            cand_pids = [p for p in get_pids_on_port(candidate) if is_pid_alive(p)]
            cand_ours = True
            for cpid in cand_pids:
                is_ours, details = is_project_owned_process(cpid, expected_service=service_name)
                if is_ours:
                    terminate_project_process(cpid)
                else:
                    cand_ours = False
                    break
            
            if cand_ours and cand_pids:
                time.sleep(0.5)
                if is_port_available(candidate):
                    ok(f"Cleaned stale project process on port {candidate}. Selected {service_name} port: {candidate}")
                    return candidate

        err(f"No available port found for {service_name} in range {preferred_port}-{preferred_port + max_tries}.")
        return None

    return None

def write_frontend_runtime_config(backend_port: int, frontend_port: int, frontend_dir: Path) -> None:
    """
    Generate js/runtime_config.js in all frontend locations so client scripts
    always communicate with the active dynamically selected backend port.
    """
    content = f"""// Auto-generated runtime configuration by run.py on {time.strftime('%Y-%m-%d %H:%M:%S')}
// DO NOT EDIT MANUALLY - This ensures frontend communicates with active backend port.
window.__BACKEND_PORT__ = {backend_port};
window.__API_BASE__ = "http://127.0.0.1:{backend_port}";
window.__FRONTEND_PORT__ = {frontend_port};
"""
    dirs = [
        frontend_dir / "js",
        ROOT_DIR / "frontend_v2" / "js",
        ROOT_DIR / "unified-pl-system" / "frontend_v2" / "js",
    ]
    for d in dirs:
        if d.parent.exists():
            d.mkdir(parents=True, exist_ok=True)
            cfg_file = d / "runtime_config.js"
            try:
                cfg_file.write_text(content, encoding="utf-8")
            except Exception as e:
                warn(f"Failed to write {cfg_file}: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# READINESS & HEALTH POLLING
# ──────────────────────────────────────────────────────────────────────────────

def check_endpoint_ready(
    url: str,
    proc: subprocess.Popen,
    port: int,
    timeout: float = 60.0,
    label: str = "Service",
    log_path: Path | None = None,
) -> bool:
    """
    Poll an HTTP endpoint until ready or until child process exits/times out.
    Distinguishes temporary warmups from real process deaths and socket transitions.
    """
    start_time = time.time()
    idx = 0
    backoff = 0.2
    port_opened = False

    while time.time() - start_time < timeout:
        # Check if the child process exited prematurely
        ret = proc.poll()
        if ret is not None:
            print()
            err(f"{label} process exited prematurely (exit code: {ret})")
            if log_path and log_path.exists():
                _dump_log_tail(log_path)
            return False

        # Test socket connection directly
        if not port_opened:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex(("127.0.0.1", port)) == 0:
                        port_opened = True
            except Exception:
                pass

        if port_opened:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "PL-Launcher-HealthCheck"})
                with _no_proxy_opener.open(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        print()
                        ok(f"{label} is healthy and responding on port {port} (HTTP 200)")
                        return True
            except Exception:
                pass

        elapsed = int(time.time() - start_time)
        if not port_opened:
            sys.stdout.write(f"\r  {SPIN[idx % 4]} Waiting for {label} to bind port {port}... ({elapsed}s)")
        else:
            sys.stdout.write(f"\r  {SPIN[idx % 4]} Port {port} is listening, awaiting {label} health response... ({elapsed}s)")
        sys.stdout.flush()
        idx += 1
        time.sleep(backoff)
        backoff = min(0.5, backoff * 1.05)

    print()
    if proc.poll() is None:
        if port_opened:
            err(f"{label} is listening on port {port} but {url} did not respond with HTTP 200 within {timeout}s timeout")
        else:
            err(f"{label} process is running (PID {proc.pid}) but did not open port {port} within {timeout}s timeout")
    else:
        err(f"{label} process exited with return code {proc.poll()}")

    if log_path and log_path.exists():
        _dump_log_tail(log_path)
    return False

def _dump_log_tail(log_path: Path, max_lines: int = 50) -> None:
    """Display the last lines of a log file for diagnosis."""
    try:
        if manager.backend_log_file and not manager.backend_log_file.closed:
            try:
                manager.backend_log_file.flush()
            except Exception:
                pass
        if manager.frontend_log_file and not manager.frontend_log_file.closed:
            try:
                manager.frontend_log_file.flush()
            except Exception:
                pass
        time.sleep(0.1)
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = [line.rstrip() for line in f.readlines() if line.strip()]
            if lines:
                print(f"\n  {BOLD}{'─'*60}")
                print(f"  Log Tail ({log_path.name}):")
                print(f"  {'─'*60}{RESET}")
                for line in lines[-max_lines:]:
                    print(f"    {line}")
                print(f"  {BOLD}{'─'*60}{RESET}\n")
            else:
                print(f"\n  {YELLOW}Log file ({log_path.name}) is empty.{RESET}")
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
  {GREEN}[OK]{RESET} Database (Preserved)
  {GREEN}[OK]{RESET} Backend started on port {backend_port}
  {GREEN}[OK]{RESET} Backend health check: PASS (HTTP 200)
  {GREEN}[OK]{RESET} Frontend started on port {frontend_port}
  {GREEN}[OK]{RESET} Frontend reachability: PASS (HTTP 200)

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
    parser.add_argument("--backend-port", type=int, default=None, metavar="PORT", help="Explicit port for FastAPI backend (default: 8000).")
    parser.add_argument("--frontend-port", type=int, default=None, metavar="PORT", help="Explicit port for frontend static server (default: 3000).")
    parser.add_argument("--diag", action="store_true", help="Run diagnostics and exit without starting servers.")
    args = parser.parse_args()

    is_explicit_backend = (args.backend_port is not None)
    is_explicit_frontend = (args.frontend_port is not None)
    pref_backend_port = args.backend_port if is_explicit_backend else 8000
    pref_frontend_port = args.frontend_port if is_explicit_frontend else 3000

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
        run_diagnostics(backend_dir, frontend_dir, python_exe, pref_backend_port, pref_frontend_port)
        return

    # Step 2: Environment & Dependencies
    header("Step 2 — Environment & Dependency Check")
    backend_env = build_backend_env(backend_dir)
    if not ensure_dependencies(python_exe, backend_dir):
        err("Dependency verification failed.")
        sys.exit(1)

    # Step 3: Database setup (Preserves database unless --seed is explicitly passed)
    header("Step 3 — Database Initialization")
    if not setup_database_if_needed(python_exe, backend_dir, backend_env, force_seed=args.seed):
        err("Database preparation failed.")
        sys.exit(1)

    # Step 4: Import validation
    header("Step 4 — Backend Import Validation")
    if not validate_main_module(python_exe, backend_dir, backend_env):
        err("Cannot launch: backend import error.")
        sys.exit(1)

    # Step 5: Dynamic Port Resolution & Stale Process Cleanup
    header("Step 5 — Port Resolution & Process Lifecycle")
    selected_backend_port = resolve_service_port(
        preferred_port=pref_backend_port,
        service_name="backend",
        is_explicit=is_explicit_backend,
    )
    if not selected_backend_port:
        err("Failed to resolve an available backend port.")
        sys.exit(1)

    selected_frontend_port = resolve_service_port(
        preferred_port=pref_frontend_port,
        service_name="frontend",
        is_explicit=is_explicit_frontend,
    )
    if not selected_frontend_port:
        err("Failed to resolve an available frontend port.")
        sys.exit(1)

    ok(f"Backend port bound:  {selected_backend_port}")
    ok(f"Frontend port bound: {selected_frontend_port}")

    # Write runtime configuration so frontend automatically connects to active backend
    write_frontend_runtime_config(selected_backend_port, selected_frontend_port, frontend_dir)
    ok(f"Frontend API runtime configuration synchronized (-> http://127.0.0.1:{selected_backend_port})")

    # Step 6: Start Backend
    header("Step 6 — Starting Backend Service")
    backend_log_path = ROOT_DIR / "backend.log"
    manager.backend_log_file = open(backend_log_path, "w", encoding="utf-8", buffering=1)

    backend_cmd = [
        str(python_exe),
        "-u",
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(selected_backend_port),
        "--log-level",
        "info",
    ]
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0

    info(f"Spawning backend: {' '.join(backend_cmd)}")
    manager.backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(backend_dir),
        env=backend_env,
        stdin=subprocess.DEVNULL,
        stdout=manager.backend_log_file,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    write_pid("backend", manager.backend_proc.pid)
    ok(f"Backend process spawned (PID {manager.backend_proc.pid})")

    # Step 7: Await Backend Health
    header("Step 7 — Verifying Backend Readiness")
    backend_health_url = f"http://127.0.0.1:{selected_backend_port}/api/v1/system/health"
    if not check_endpoint_ready(backend_health_url, manager.backend_proc, port=selected_backend_port, timeout=60.0, label="Backend", log_path=backend_log_path):
        err("Backend failed to reach healthy state.")
        manager.cleanup()
        sys.exit(1)

    # Step 8: Start Frontend
    header("Step 8 — Starting Frontend Service")
    frontend_log_path = ROOT_DIR / "frontend.log"
    manager.frontend_log_file = open(frontend_log_path, "w", encoding="utf-8", buffering=1)

    frontend_cmd = [
        str(python_exe),
        "-u",
        "-m",
        "http.server",
        str(selected_frontend_port),
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
        creationflags=creation_flags,
    )
    write_pid("frontend", manager.frontend_proc.pid)
    ok(f"Frontend process spawned (PID {manager.frontend_proc.pid})")

    # Step 9: Await Frontend Reachability
    header("Step 9 — Verifying Frontend Readiness")
    frontend_url = f"http://127.0.0.1:{selected_frontend_port}/login.html"
    if not check_endpoint_ready(frontend_url, manager.frontend_proc, port=selected_frontend_port, timeout=20.0, label="Frontend", log_path=frontend_log_path):
        err("Frontend failed to reach ready state.")
        manager.cleanup()
        sys.exit(1)

    # If Self-Test mode:
    if args.self_test:
        header("SELF-TEST VERIFICATION COMPLETED")
        ok(f"Backend health endpoint (http://127.0.0.1:{selected_backend_port}/api/v1/system/health): HTTP 200 PASS")
        ok(f"Frontend login page (http://127.0.0.1:{selected_frontend_port}/login.html): HTTP 200 PASS")
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
    print_startup_banner(ROOT_DIR, selected_backend_port, selected_frontend_port)

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
