#!/usr/bin/env python3
"""XUNIA / CL1 biological data center — zero-dependency local telemetry.

Public xunia.org serves ONLY the static ontology. This operator-only service
serves the same website on 127.0.0.1 and adds read-only, consent-by-launch
telemetry (loopback TCP reachability + basic host load/free disk). It does not
access bank accounts, private vaults, biosensors, model prompts or cloud APIs.
"""
from __future__ import annotations

import argparse
import errno
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BIO = DOCS / "biological-data-center"
GENOME = DOCS / "ecosystem-observatory" / "snapshot.json"
PORTS = {"ollama": 11434, "cl1": 8787, "jukebox": 8844, "aura": 8866, "nexus": 8791}
STATIC_PATHS = {
    "/biological-data-center/": (BIO / "index.html", "text/html; charset=utf-8"),
    "/biological-data-center/index.html": (BIO / "index.html", "text/html; charset=utf-8"),
    "/biological-data-center/style.css": (BIO / "style.css", "text/css; charset=utf-8"),
    "/biological-data-center/app.js": (BIO / "app.js", "text/javascript; charset=utf-8"),
    "/biological-data-center/ontology.json": (BIO / "ontology.json", "application/json; charset=utf-8"),
    "/ecosystem-observatory/snapshot.json": (GENOME, "application/json; charset=utf-8"),
}
CSP = (
    "default-src 'self'; connect-src 'self'; script-src 'self'; "
    "style-src 'self'; img-src 'self' data:; font-src 'none'; "
    "object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'"
)


def probe_loopback(port: int) -> str:
    """TCP listening is not proof of the process identity or service health."""
    if type(port) is not int or port < 1 or port > 65535:
        return "UNTESTED"
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.12):
            return "LISTENING"
    except OSError:
        return "OFFLINE"


def telemetry_snapshot() -> dict[str, object]:
    services = {name: probe_loopback(port) for name, port in PORTS.items()}
    host: dict[str, object] = {
        "load_1m": None,
        "logical_cpu_count": None,
        "disk_free_gb": None,
    }
    try:
        host["load_1m"] = round(float(os.getloadavg()[0]), 2)
    except (OSError, AttributeError, ValueError):
        pass
    try:
        value = os.cpu_count()
        if isinstance(value, int) and 0 < value < 10000:
            host["logical_cpu_count"] = value
    except OSError:
        pass
    try:
        host["disk_free_gb"] = round(shutil.disk_usage(Path.home()).free / (1024 ** 3), 1)
    except (OSError, ValueError):
        pass
    return {
        "schema": "xunia.cl1.local-telemetry.v1",
        "source": "127.0.0.1",
        "public": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "services": services,
        "host": host,
        "provenance": "operator-started-local-python",
        "confidence": "TCP listening only; not application identity or biological hardware",
        "bank_accounts_connected": False,
        "vault_unlocked": False,
        "biohardware_connected": False,
    }


def ontology_valid() -> bool:
    try:
        data = json.loads((BIO / "ontology.json").read_text(encoding="utf-8"))
        nodes = data["nodes"]
        edges = data["edges"]
        ids = {node["id"] for node in nodes}
        return (
            data["schema"] == "xunia.cl1.biological-data-center.v1"
            and len(nodes) > 20
            and len(ids) == len(nodes)
            and len(edges) > 30
            and all(edge["from"] in ids and edge["to"] in ids for edge in edges)
            and data["security"]["paid_services"] is False
            and data["security"]["biological_devices_connected"] is False
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


class BioHandler(BaseHTTPRequestHandler):
    server_version = "XUNIA-CL1/1.0"
    sys_version = ""

    def _headers(self, content_type: str, size: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)

    def _valid_client(self) -> bool:
        # A Host guard also limits browser DNS-rebinding attempts.
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host", "").lower() not in allowed:
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in allowed}:
            return False
        if self.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
            # Opening a localhost link from ChatGPT, email, or another site
            # is a *top-level navigation*, not a cross-origin API request.
            # Allow only that safe document entry; never expose telemetry
            # or arbitrary assets to a cross-site fetch/navigation.
            entry = urlsplit(self.path).path
            return (
                self.command == "GET"
                and entry in {
                    "/", "/biological-data-center/",
                    "/biological-data-center/index.html",
                }
                and self.headers.get("Sec-Fetch-Mode", "").lower() == "navigate"
                and self.headers.get("Sec-Fetch-Dest", "").lower() == "document"
            )
        return True

    def _respond(self, code: int, data: bytes, mime: str, *, head: bool = False) -> None:
        self.send_response(code)
        self._headers(mime, len(data))
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def _handle(self, *, head: bool = False) -> None:
        if not self._valid_client():
            self._respond(403, b"Access denied", "text/plain; charset=utf-8", head=head)
            return
        path = urlsplit(self.path).path
        if path == "/":
            # Minimal redirect to the local XUNIA Biological Data Center route.
            self.send_response(302)
            self.send_header("Location", "/biological-data-center/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        if path == "/api/telemetry":
            raw = json.dumps(telemetry_snapshot(), separators=(",", ":")).encode("utf-8")
            self._respond(200, raw, "application/json; charset=utf-8", head=head)
            return
        entry = STATIC_PATHS.get(path)
        if entry is None:
            self._respond(404, b"Not found", "text/plain; charset=utf-8", head=head)
            return
        file, mime = entry
        try:
            raw = file.read_bytes()
        except OSError:
            self._respond(503, b"Source unavailable", "text/plain; charset=utf-8", head=head)
            return
        self._respond(200, raw, mime, head=head)

    def do_GET(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle(head=True)

    def do_POST(self) -> None:
        self._respond(405, b"Read-only service", "text/plain; charset=utf-8")

    def do_PUT(self) -> None:
        self._respond(405, b"Read-only service", "text/plain; charset=utf-8")

    def do_OPTIONS(self) -> None:
        self._respond(405, b"No cross-origin API", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args: object) -> None:
        # Suppress access path logs (URLs can accidentally contain private text).
        return


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="XUNIA CL1 local biological data center")
    parser.add_argument("--port", type=int, default=8871, help="Local web port (default: 8871)")
    parser.add_argument("--check", action="store_true", help="Validate ontology without opening a port")
    args = parser.parse_args(argv)
    if not ontology_valid():
        print("XUNIA CL1: ontology validation failed", flush=True)
        return 2
    if args.check:
        print("XUNIA CL1: ontology valid; local-only; no bank/biohardware/paid APIs", flush=True)
        return 0
    if not (1024 <= args.port <= 65535):
        parser.error("--port must be 1024–65535")
    try:
        with ThreadingHTTPServer(("127.0.0.1", args.port), BioHandler) as server:
            server.daemon_threads = True
            print(f"XUNIA BIOLOGICAL DATA CENTER / http://127.0.0.1:{args.port}/", flush=True)
            print("Read-only CL1 telemetry; public xunia.org is static. Ctrl+C to stop.", flush=True)
            server.serve_forever(poll_interval=0.4)
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(f"XUNIA CL1: port {args.port} already belongs to a running process.", flush=True)
            print(f"Inspect safely: lsof -nP -iTCP:{args.port} -sTCP:LISTEN", flush=True)
            print("If this is your earlier XUNIA Bio terminal tab, press Ctrl+C there", flush=True)
            print("then rerun: cd ~/xunia-bio-cl1 && bash scripts/xunia-bio", flush=True)
            print("No process was stopped, overwritten, or replaced.", flush=True)
        else:
            print("XUNIA CL1: cannot start local HTTP listener; existing services untouched.", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
