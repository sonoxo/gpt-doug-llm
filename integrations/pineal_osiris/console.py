#!/usr/bin/env python3
"""Loopback-only, read-only OSIRIS/PINEAL operations console.

Never serves raw OSIRIS feeds or arbitrary files. Browser receives only
sanitized health observations from stack.status(), not intelligence payloads.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Callable
from urllib.parse import urlsplit

ASSETS = Path(__file__).resolve().parent
STATIC = {
    "/": ("console.html", "text/html; charset=utf-8"),
    "/app.js": ("console.js", "text/javascript; charset=utf-8"),
    "/style.css": ("console.css", "text/css; charset=utf-8"),
}
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; img-src 'self'; font-src 'none'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    ),
}


class ConsoleServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int, status_provider: Callable[[], dict]):
        self.status_provider = status_provider
        super().__init__(("127.0.0.1", port), ConsoleHandler)


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "PinealOsirisConsole/1.0"
    sys_version = ""

    def log_message(self, fmt: str, *args: object) -> None:
        # This is an operator-local status console; no API responses or secrets in logs.
        return

    def _send(self, code: int, body: bytes, mime: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        for header, value in SECURITY_HEADERS.items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        port = self.server.server_port
        accepted_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host") not in accepted_hosts:
            self._send(403, b"Forbidden", "text/plain; charset=utf-8")
            return
        path = urlsplit(self.path).path
        if path == "/api/status":
            try:
                safe_status = self.server.status_provider()
                content = json.dumps(safe_status, sort_keys=True, allow_nan=False).encode("utf-8")
            except (OSError, TypeError, ValueError) as exc:
                # Fail closed and avoid echoing internal filesystem paths.
                self._send(503, b'{"status":"UNAVAILABLE"}', "application/json")
                return
            self._send(200, content, "application/json; charset=utf-8")
            return
        if path in STATIC:
            filename, mime = STATIC[path]
            try:
                content = (ASSETS / filename).read_bytes()
            except OSError:
                self._send(503, b"Dashboard asset unavailable", "text/plain; charset=utf-8")
                return
            self._send(200, content, mime)
            return
        self._send(404, b"Not found", "text/plain; charset=utf-8")


def launch_console(port: int, status_provider: Callable[[], dict]) -> ConsoleServer:
    if not 1024 <= port <= 65535:
        raise ValueError("console port must be 1024..65535")
    server = ConsoleServer(port, status_provider)
    worker = threading.Thread(target=server.serve_forever,
                              name="pineal-osiris-readonly-console", daemon=True)
    worker.start()
    return server
