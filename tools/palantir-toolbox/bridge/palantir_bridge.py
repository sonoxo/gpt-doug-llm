#!/usr/bin/env python3
"""Local, read-first bridge between the Chrome extension and palantir_foundry.py.

Credentials stay in environment variables consumed by FoundryClient. The bridge
binds only to 127.0.0.1 and requires PALANTIR_TOOLBOX_BRIDGE_KEY on every request.
"""

from __future__ import annotations

import hmac
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from palantir_foundry import FoundryClient, FoundryError  # noqa: E402

HOST = "127.0.0.1"
PORT = int(os.getenv("PALANTIR_TOOLBOX_PORT", "8765"))
BRIDGE_KEY = os.getenv("PALANTIR_TOOLBOX_BRIDGE_KEY", "").strip()


def _client() -> FoundryClient:
    client = FoundryClient.from_environment()
    if client is None:
        raise RuntimeError("Foundry is not configured. Set FOUNDRY_BASE_URL and credentials.")
    return client


def _segments(path: str) -> list[str]:
    return [urllib.parse.unquote(p) for p in path.strip("/").split("/") if p]


class Handler(BaseHTTPRequestHandler):
    server_version = "PalantirToolboxBridge/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[palantir-toolbox] " + (fmt % args) + "\n")

    def _origin(self) -> str:
        origin = self.headers.get("Origin", "")
        return origin if origin.startswith("chrome-extension://") else ""

    def _cors(self) -> None:
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Palantir-Toolbox-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _authorized(self) -> bool:
        if not BRIDGE_KEY:
            return False
        supplied = self.headers.get("X-Palantir-Toolbox-Key", "")
        return hmac.compare_digest(supplied, BRIDGE_KEY)

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _require_auth(self) -> bool:
        if not self._origin():
            self._send(403, {"ok": False, "error": "Chrome extension origin required"})
            return False
        if not self._authorized():
            self._send(401, {"ok": False, "error": "Invalid bridge key"})
            return False
        return True

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        if length > 1_000_000:
            raise ValueError("Request body too large")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        try:
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            page_size = max(1, min(int(query.get("pageSize", ["100"])[0]), 1000))
            parts = _segments(parsed.path)
            client = _client()

            if parts == ["health"]:
                status = client.status()
                status["writes_enabled"] = False
                self._send(200, {"ok": True, "bridge": "local-read-first", "foundry": status})
                return

            if parts == ["ontologies"]:
                self._send(200, client.list_ontologies(page_size=page_size))
                return

            if len(parts) == 3 and parts[0] == "ontologies" and parts[2] == "object-types":
                self._send(200, client.list_object_types(parts[1], page_size=page_size))
                return

            if len(parts) == 4 and parts[0] == "ontologies" and parts[2] == "objects":
                self._send(200, client.list_objects(parts[1], parts[3], page_size=page_size))
                return

            self._send(404, {"ok": False, "error": "Unknown read endpoint"})
        except (ValueError, RuntimeError, FoundryError) as exc:
            self._send(400, {"ok": False, "error": str(exc)[:1000]})
        except Exception as exc:  # fail closed without traceback over HTTP
            self.log_message("unexpected error: %s", exc)
            self._send(500, {"ok": False, "error": "Bridge request failed"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        try:
            parsed = urllib.parse.urlparse(self.path)
            parts = _segments(parsed.path)
            body = self._json_body()
            client = _client()

            if len(parts) == 5 and parts[0] == "ontologies" and parts[2] == "objects" and parts[4] == "search":
                self._send(200, client.search_objects(parts[1], parts[3], body))
                return

            self._send(404, {"ok": False, "error": "Unknown POST endpoint; bridge is read-first"})
        except (ValueError, RuntimeError, FoundryError) as exc:
            self._send(400, {"ok": False, "error": str(exc)[:1000]})
        except Exception as exc:
            self.log_message("unexpected error: %s", exc)
            self._send(500, {"ok": False, "error": "Bridge request failed"})


def main() -> int:
    if not BRIDGE_KEY:
        print("PALANTIR_TOOLBOX_BRIDGE_KEY is required; refusing to start.", file=sys.stderr)
        return 2
    try:
        client = _client()
        status = client.status()
    except Exception as exc:
        print(f"Foundry configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"Palantir Toolbox bridge: http://{HOST}:{PORT}")
    print(f"Foundry host: {status['host']}")
    print("Mode: read-first; action writes are not exposed by this bridge")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
