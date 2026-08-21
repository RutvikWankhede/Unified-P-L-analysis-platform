import os
import sys
import subprocess

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    run_script = os.path.join(script_dir, "run.py")
    sys.exit(subprocess.call([sys.executable, run_script] + sys.argv[1:]))
