import http.server
import socketserver
import os

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        super().end_headers()

socketserver.TCPServer.allow_reuse_address = True
PORT = 3000

# Change to the directory this script is in (which will be frontend_v2)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

httpd = socketserver.TCPServer(('', PORT), NoCacheHandler)
print(f"Serving HTTP on 0.0.0.0 port {PORT} (http://0.0.0.0:{PORT}/) ...")
httpd.serve_forever()
