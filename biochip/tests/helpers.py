"""Test-only local HTTP fixtures. Never connect to a real inference service."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch


class HTTPFixture:
    def __init__(self, respond=None):
        self.requests = []
        self.respond = respond or (lambda handler, body: self.reply(handler, {'models': []}))
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.requests.append((self.command, self.path, None))
                fixture.respond(self, None)
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                fixture.requests.append((self.command, self.path, body))
                fixture.respond(self, body)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.url = 'http://127.0.0.1:' + str(self.server.server_port)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)

    @staticmethod
    def reply(handler, value, *, status=200, headers=None):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode('utf-8')
        handler.send_response(status)
        for key, val in (headers or {}).items():
            handler.send_header(key, str(val))
        handler.end_headers()
        try:
            handler.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)


@contextmanager
def stop_environment():
    with tempfile.TemporaryDirectory() as directory:
        with patch.dict(os.environ, {
            'GPT_DOUG_AI_STOP_DIR': directory,
            'GPT_DOUG_AI_BLOCK_ALL': '0',
            'GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY': '1',
        }):
            yield Path(directory)
