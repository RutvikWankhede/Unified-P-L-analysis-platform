import http.server
import socketserver
import urllib.request
import urllib.error
import threading
import os
import socket

PORT = 3003
DIRECTORY = r"C:\Users\HP\.gemini\antigravity-ide\scratch\P&L system\frontend_v2"
API_BACKEND = "http://127.0.0.1:8000"

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def proxy_request(self, method):
        if not self.path.startswith('/api'):
            if method == "GET":
                super().do_GET()
            else:
                self.send_error(405)
            return

        url = API_BACKEND + self.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        headers = {}
        for k, v in self.headers.items():
            if k.lower() not in ['host', 'connection']:
                headers[k] = v

        print(f"PROXYING {method} {url} with Headers: {headers}")

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for k, v in response.headers.items():
                    if k.lower() not in ['transfer-encoding']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self): self.proxy_request("GET")
    def do_POST(self): self.proxy_request("POST")
    def do_PUT(self): self.proxy_request("PUT")
    def do_DELETE(self): self.proxy_request("DELETE")
    def do_OPTIONS(self): self.proxy_request("OPTIONS")

Handler = ProxyHTTPRequestHandler

class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

with ReusableTCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
