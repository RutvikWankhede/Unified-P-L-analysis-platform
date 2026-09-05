import subprocess, os, time
import sys

def main():
    print("Starting Candidate Backend on 8001...")
    backend_env = os.environ.copy()
    backend_dir = os.path.abspath('PRE18_CANDIDATE_RESTORE_2026-08-21/backend/backend')
    backend_env['PYTHONPATH'] = backend_dir
    python_exe = os.path.abspath('unified-pl-system/venv/Scripts/python.exe')
    
    print("Seeding candidate DB...")
    subprocess.run([python_exe, 'seed.py'], cwd=backend_dir)
    
    backend_proc = subprocess.Popen([python_exe, '-u', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8001'], cwd=backend_dir, env=backend_env)
    
    print("Starting Candidate Frontend on 3001...")
    frontend_dir = os.path.abspath('PRE18_CANDIDATE_RESTORE_2026-08-21/frontend')
    frontend_proc = subprocess.Popen([python_exe, '-u', '-m', 'http.server', '3001'], cwd=frontend_dir)
    
    print("Candidate running at http://127.0.0.1:3001/login.html")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == '__main__':
    main()
