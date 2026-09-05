import os
import sys
import subprocess
from pathlib import Path

root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "unified-pl-system" / "backend"
frontend_dir = root_dir / "frontend_v2"
venv_python = root_dir / "unified-pl-system" / "venv" / "Scripts" / "python.exe"
python_exe = str(venv_python) if venv_python.exists() else sys.executable

env = os.environ.copy()
env["PYTHONPATH"] = str(backend_dir)

print(f"Using python: {python_exe}")
print(f"Backend dir: {backend_dir}")

# Start backend process
p_backend = subprocess.Popen(
    [python_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=str(backend_dir),
    env=env
)

# Start frontend process
p_frontend = subprocess.Popen(
    [python_exe, "serve_frontend.py"],
    cwd=str(frontend_dir)
)

print(f"Processes started: Backend PID {p_backend.pid}, Frontend PID {p_frontend.pid}")

p_backend.wait()
p_frontend.wait()
