import sys
import os
import time
import threading
from pathlib import Path
import http.server
import socketserver

# Force UTF-8 output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parent
backend_dir = root_dir / "unified-pl-system" / "backend"
frontend_dir = root_dir / "frontend_v2"

# Ensure backend_dir is in sys.path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import uvicorn
import main

def run_backend():
    print(f"[Backend] Starting Uvicorn with main.app on 127.0.0.1:8000...")
    config = uvicorn.Config(app=main.app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config=config)
    server.run()

def run_frontend():
    print(f"[Frontend] Starting static server on 127.0.0.1:3000...")
    class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(frontend_dir), **kwargs)
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            super().end_headers()

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('0.0.0.0', 3000), NoCacheHandler)
    httpd.serve_forever()

t1 = threading.Thread(target=run_backend, daemon=True)
t2 = threading.Thread(target=run_frontend, daemon=True)

t1.start()
t2.start()

print("[Launcher] Both backend and frontend servers started in threads. Warming up...")
time.sleep(4)
print("[Launcher] Dev Server ready!")

while True:
    time.sleep(1)
