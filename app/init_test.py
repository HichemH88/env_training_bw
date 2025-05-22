#!/usr/bin/env python3
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import time

# Simple HTTP server to test container health
class HealthHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    host = '0.0.0.0'
    port = 8000
    server = HTTPServer((host, port), HealthHandler)
    print(f"Server running on http://{host}:{port}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()