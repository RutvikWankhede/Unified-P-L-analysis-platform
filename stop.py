import os
import signal
import subprocess
import sys
import platform

def kill_process_on_port(port):
    """Kills any process listening on the specified port."""
    system = platform.system()
    try:
        if system == "Windows":
            # Find PID using netstat
            cmd = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd, shell=True, text=True)
            for line in output.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    if pid != '0':
                        print(f"Killing process {pid} on port {port}")
                        subprocess.call(['taskkill', '/F', '/PID', pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Find PID using lsof on macOS/Linux
            cmd = f'lsof -t -i:{port}'
            output = subprocess.check_output(cmd, shell=True, text=True)
            for pid in output.strip().split('\n'):
                if pid:
                    print(f"Killing process {pid} on port {port}")
                    os.kill(int(pid), signal.SIGKILL)
    except subprocess.CalledProcessError:
        print(f"No process found listening on port {port}.")
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")

if __name__ == "__main__":
    print("Stopping Unified P&L AI Platform...")
    kill_process_on_port(8000)
    kill_process_on_port(3000)
    print("Done.")
