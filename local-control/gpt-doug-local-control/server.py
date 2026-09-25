from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from agent_core import execute, armed, arm, disarm, panic, clear_panic, panic_active, ROOT, RUNTIME, POLICY

TOKEN_FILE = RUNTIME / "token.txt"
HEARTBEAT_FILE = RUNTIME / "heartbeat.json"
if not TOKEN_FILE.exists():
    TOKEN_FILE.write_text(secrets.token_urlsafe(32))
TOKEN = TOKEN_FILE.read_text().strip()
try:
    TOKEN_FILE.chmod(0o600)
except Exception:
    pass

INDEX = (ROOT / "static" / "index.html").read_bytes()
ALLOWED_HOSTS = {"127.0.0.1:8765", "localhost:8765", "[::1]:8765"}


def authority_state() -> str:
    if panic_active():
        return "PANIC"
    if armed():
        return "ARMED"
    return "DISARMED"


def heartbeat_loop() -> None:
    interval = max(1, int(POLICY.get("heartbeat_interval_seconds", 2)))
    while True:
        payload = {
            "ts": time.time(),
            "state": authority_state(),
            "loopback": True,
            "intervalSeconds": interval,
        }
        try:
            HEARTBEAT_FILE.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass
        time.sleep(interval)


class Handler(BaseHTTPRequestHandler):
    server_version = "GPTDougLocal/0.2"

    def _headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")

    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    def _json(self, status, obj):
        raw = json.dumps(obj).encode()
        self.send_response(status)
        self._headers("application/json", len(raw))
        self.end_headers()
        self.wfile.write(raw)

    def _auth(self):
        return self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def _local_request(self) -> bool:
        return self.client_address[0] in {"127.0.0.1", "::1"} and self._host_ok()

    def do_GET(self):
        if not self._local_request():
            return self._json(403, {"error": "loopback host only"})
        p = urlparse(self.path).path
        if p == "/":
            self.send_response(200)
            self._headers("text/html; charset=utf-8", len(INDEX))
            self.end_headers()
            self.wfile.write(INDEX)
            return
        if p == "/status":
            heartbeat = None
            try:
                heartbeat = json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
            return self._json(200, {
                "state": authority_state(),
                "armed": armed(),
                "panic": panic_active(),
                "loopback": True,
                "heartbeat": heartbeat,
            })
        if p == "/token":
            return self._json(200, {"token": TOKEN})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._local_request():
            return self._json(403, {"error": "loopback host only"})
        if not self._auth():
            return self._json(401, {"error": "bad token"})
        n = int(self.headers.get("Content-Length", "0") or "0")
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            p = urlparse(self.path).path
            if p == "/arm":
                out = arm(body.get("seconds"))
            elif p == "/disarm":
                disarm(); out = {"armed": False, "state": authority_state()}
            elif p == "/panic":
                panic(); out = {"panic": True, "state": authority_state()}
            elif p == "/clear-panic":
                clear_panic(); out = {"panic": False, "state": authority_state()}
            elif p == "/execute":
                out = execute(body)
            else:
                return self._json(404, {"error": "not found"})
            self._json(200, out)
        except Exception as e:
            self._json(400, {"error": str(e), "state": authority_state()})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    threading.Thread(target=heartbeat_loop, daemon=True, name="gpt-doug-heartbeat").start()
    print("GPT-Doug Local Control v0.2")
    print("URL: http://127.0.0.1:8765")
    print(f"Token file: {TOKEN_FILE}")
    print("Authority: DISARMED by default; heartbeat loop: 2s")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
