#!/usr/bin/env python3
"""Local browser dashboard for ZYRAPALANTIR field decision support.

Binds to loopback by default and visualizes the existing read-only field snapshot.
The right-hand display is a non-geographic system topology, not a targeting map.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "zyrapalantir-field"

spec = importlib.util.spec_from_file_location("zyrapalantir_field", ROOT / "scripts" / "zyrapalantir_field.py")
field = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(field)


def assistant_reply(prompt: str, state: dict) -> str:
    text = prompt.lower().strip()
    if not text:
        return "Ask about readiness, cyber findings, communications, assets, or incidents."
    if any(k in text for k in ("ready", "readiness", "status")):
        return (
            f"Field readiness is {'READY' if state.get('field_ready') else 'DEGRADED/PENDING'}. "
            f"Defense={'ACTIVE' if state.get('defense_profile_active') else 'INACTIVE'}, "
            f"LIVE={'RUNNING' if state.get('live_service_running') else 'STOPPED'}, "
            f"Maven={'PASS' if state.get('maven_ok') else 'NOT READY'}, "
            f"REDPANDA={'PASS' if state.get('redpanda_cpr_ok') else 'NOT READY'}."
        )
    if any(k in text for k in ("cyber", "finding", "alert", "threat")):
        c = state.get("cyber", {})
        counts = c.get("severity_counts", {})
        return (
            "Current defensive findings: "
            f"LOW={counts.get('LOW',0)}, MEDIUM={counts.get('MEDIUM',0)}, "
            f"HIGH={counts.get('HIGH',0)}, CRITICAL={counts.get('CRITICAL',0)}. "
            f"Highest severity is {state.get('highest_severity','UNKNOWN')}."
        )
    if any(k in text for k in ("comms", "network", "link")):
        c = state.get("comms", {})
        return (
            f"Local defensive comms view: interface={c.get('default_route_interface','unknown')}; "
            f"addresses={', '.join(c.get('local_addresses', [])[:4]) or 'none'}. "
            "This console does not reconfigure or disrupt networks."
        )
    if any(k in text for k in ("asset", "host", "device")):
        a = state.get("local_asset", {})
        return (
            f"Local asset: {a.get('hostname','unknown')} running {a.get('system','unknown')} "
            f"{a.get('release','')} on {a.get('machine','unknown')}."
        )
    if "incident" in text:
        return (
            "Analyst attention is "
            f"{'REQUIRED' if state.get('analyst_attention_required') else 'NOT CURRENTLY REQUIRED'}. "
            "Any external response remains human-authorized."
        )
    return "I can summarize readiness, cyber findings, communications, assets, and incidents from the local ZYRAPALANTIR field snapshot."


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: pathlib.Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            self._json(field.snapshot(None))
            return
        if parsed.path == "/api/assistant":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            state = field.snapshot(None)
            self._json({"reply": assistant_reply(q, state), "state_timestamp": state.get("timestamp")})
            return
        if parsed.path in ("/", "/index.html"):
            self._file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        self.send_error(404)

    def log_message(self, fmt: str, *args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(prog="zyra-field visual")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback bind by default; visual console is local-only.")

    url = f"http://127.0.0.1:{args.port}/"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("🎖️ ZYRAPALANTIR VISUAL FIELD OPS")
    print("🛰️ local defensive telemetry + human decision support")
    print("🗺️ right panel is NON-GEOGRAPHIC system topology")
    print("⛔ targeting/weapons/automatic external action: DISABLED")
    print(f"🌐 {url}")
    print("Press Ctrl-C to stop the visual console.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print("✅ Visual console stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
