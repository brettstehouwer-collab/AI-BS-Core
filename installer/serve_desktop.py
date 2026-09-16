"""
AI-BS Sovereign Intelligence Studio - Local Desktop Static SPA Web Server
High-performance, zero-dependency Python 3 static HTTP server with SPA fallback routing.
Designed for offline desktop execution of AI-BS Sovereign Studio and AI-BS Broadcast Studio.
"""

import os
import sys
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Pre-register critical MIME types
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('audio/mpeg', '.mp3')
mimetypes.add_type('audio/ogg', '.ogg')

DEFAULT_PORT = 5173
HOST = '127.0.0.1'


def determine_serve_dir(port=DEFAULT_PORT, custom_dir=None):
    if custom_dir and os.path.isdir(custom_dir):
        return os.path.abspath(custom_dir)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()

    if port == 5174:
        possible_paths = [
            os.path.join(script_dir, 'broadcast_dist'),
            r'C:\AI-BS\BroadcastStudioApp\dist',
            os.path.join(script_dir, '..', 'BroadcastStudioApp', 'dist'),
            os.path.join(cwd, 'broadcast_dist'),
            os.path.join(cwd, 'BroadcastStudioApp', 'dist'),
        ]
    else:
        possible_paths = [
            r'C:\AI-BS\frontend\dist',
            os.path.join(script_dir, '..', 'frontend', 'dist'),
            os.path.join(script_dir, 'frontend_dist'),
            os.path.join(script_dir, 'dist'),
            os.path.join(cwd, 'frontend_dist'),
            os.path.join(cwd, 'frontend', 'dist'),
        ]

    for p in possible_paths:
        if os.path.exists(os.path.join(p, 'index.html')):
            return os.path.abspath(p)

    # Fallback initialization
    fallback_name = 'broadcast_dist' if port == 5174 else 'frontend_dist'
    fallback_dir = os.path.join(script_dir, fallback_name)
    os.makedirs(fallback_dir, exist_ok=True)
    index_path = os.path.join(fallback_dir, 'index.html')
    if not os.path.exists(index_path):
        app_title = "AI-BS Broadcast Studio" if port == 5174 else "AI-BS Sovereign Studio"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(f'<!DOCTYPE html><html><head><title>{app_title}</title></head><body><h1>{app_title}</h1><p>Initializing desktop assets...</p></body></html>')
    return fallback_dir


class SPAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=self.server.serve_dir, **kwargs)

    def do_GET(self):
        serve_dir = self.server.serve_dir
        # Clean path
        clean_path = self.path.split('?')[0].split('#')[0]
        local_path = os.path.join(serve_dir, clean_path.lstrip('/'))

        # If file exists, serve standard static asset
        if os.path.isfile(local_path):
            return super().do_GET()

        # If directory requested and index.html exists, serve standard
        if os.path.isdir(local_path) and os.path.isfile(os.path.join(local_path, 'index.html')):
            return super().do_GET()

        # Otherwise, if it has no extension or is not found, fallback to root index.html (SPA routing)
        self.path = '/index.html'
        return super().do_GET()

    def end_headers(self):
        # Enable CORS for local backend communications and Web Workers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        # Suppress spammy asset logs in desktop console
        pass


def run_server(start_port=DEFAULT_PORT, custom_dir=None):
    port = start_port
    max_port = start_port + 20
    httpd = None

    serve_dir = determine_serve_dir(start_port, custom_dir)

    while port < max_port:
        try:
            httpd = ThreadingHTTPServer((HOST, port), SPAHandler)
            httpd.serve_dir = serve_dir
            break
        except OSError:
            port += 1

    if not httpd:
        print(f"[ERROR] Could not bind to any port between {start_port} and {max_port}", flush=True)
        sys.exit(1)

    print(f"[AI-BS] Local Desktop Web Server online at: http://{HOST}:{port}", flush=True)
    print(f"[AI-BS] Serving distribution bundle from: {serve_dir}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("[AI-BS] Server terminated by user.", flush=True)
        httpd.server_close()


if __name__ == '__main__':
    specified_port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else DEFAULT_PORT
    specified_dir = sys.argv[2] if len(sys.argv) > 2 else None
    run_server(specified_port, specified_dir)
