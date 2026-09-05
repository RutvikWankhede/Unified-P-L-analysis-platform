import os
import subprocess
import time

def kill_port(port):
    try:
        out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True).decode()
        for line in out.strip().split('\n'):
            parts = [p for p in line.strip().split() if p]
            if len(parts) >= 5 and f":{port}" in parts[1]:
                pid = parts[-1]
                print(f"Killing PID {pid} on port {port}")
                os.system(f"taskkill /F /PID {pid} >nul 2>&1")
    except Exception as e:
        pass

kill_port(8000)
kill_port(3000)
print("Ports cleaned.")
