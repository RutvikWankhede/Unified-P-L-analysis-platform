import subprocess, sys, os

backend_dir = r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\backend'
python = r'c:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\unified-pl-system\venv\Scripts\python.exe'

env = os.environ.copy()
env['PYTHONPATH'] = backend_dir

proc = subprocess.run(
    [python, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000', '--log-level', 'info'],
    cwd=backend_dir,
    capture_output=True,
    text=True,
    timeout=45,
    env=env
)
print("STDOUT:", proc.stdout[-3000:] if proc.stdout else "(empty)")
print("STDERR:", proc.stderr[-3000:] if proc.stderr else "(empty)")
print("Return code:", proc.returncode)
