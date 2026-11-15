#!/usr/bin/env python3
"""CL1-AURA browser fallback for terminals that do not report clicks.

Runs a static *local* spatial frontend on 127.0.0.1 only. Its JSON API
contains architecture metadata and loopback TCP statuses, never secrets,
private-vault contents, bank accounts, shell execution or external APIs.
"""
from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from eco_shaggoth_cl1 import health_snapshot, topology

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "apps" / "cl1-aura"
PORT = 8866
ASSET_PATHS = frozenset(("/", "/index.html", "/aura.js", "/style.css"))


class AuraHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory or str(ASSETS), **kwargs)

    def _trusted_host(self) -> bool:
        expected = {
            "127.0.0.1:" + str(self.server.server_port),
            "localhost:" + str(self.server.server_port),
        }
        return self.headers.get("Host", "").lower() in expected

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self'; font-src 'none'; "
                         "frame-ancestors 'none'; form-action 'none'")
        super().end_headers()

    def _json_response(self, value: dict) -> None:
        data = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if not self._trusted_host():
            self.send_error(403, "Untrusted Host")
            return
        path = urlsplit(self.path).path
        if path == "/api/topology":
            self._json_response(topology())
            return
        if path == "/api/status":
            self._json_response({
                "schema": "cl1-aura/status-v1",
                "health": health_snapshot(),
                "note": "LISTENING = local TCP accepts connections, NOT authenticated identity",
                "bank_accounts_connected": False,
                "vault_unlocked": False,
            })
            return
        if path not in ASSET_PATHS:
            self.send_error(404)
            return
        # Strip query parameters to avoid file handling ambiguity.
        self.path = path
        super().do_GET()

    def do_POST(self) -> None:
        self.send_error(405, "Read-only AURA frontend")

    def log_message(self, format: str, *args) -> None:
        # Keep local access logs minimal; do not record arbitrary request paths.
        pass


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CL1-AURA local clickable spatial UI")
    parser.add_argument("--port", type=int, default=PORT, help="Local port (default 8866)")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be in 1024..65535")
    if not (ASSETS / "index.html").is_file():
        parser.error("local CL1-AURA UI assets missing")
    try:
        with ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            partial(AuraHandler, directory=str(ASSETS)),
        ) as server:
            server.daemon_threads = True
            print("CL1-AURA interactive spatial UI at http://127.0.0.1:" + str(args.port), flush=True)
            print("Mouse: select nodes, drag to rotate, wheel zoom, click layers. Ctrl+C exits.", flush=True)
            server.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print("CL1-AURA cannot bind local port; leave existing services intact.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
