#!/usr/bin/env python3
"""Interactive local browser dashboard for ZYRAPALANTIR field decision support.

The service binds to loopback only, visualizes local defensive state, and exposes
read-only investigation/readiness/audit views. It does not select targets,
control weapons, issue fires, steer vehicles, or perform automatic external
actions.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "zyrapalantir-field"
STATE_DIR = pathlib.Path.home() / ".config" / "gpt-doug"
LIVE_AUDIT = STATE_DIR / "zyrapalantir-live-audit.jsonl"

spec = importlib.util.spec_from_file_location("zyrapalantir_field", ROOT / "scripts" / "zyrapalantir_field.py")
field = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(field)


def _tail_jsonl(path: pathlib.Path, limit: int = 30) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except Exception:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def investigations(state: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    findings = state.get("cyber", {}).get("findings", [])
    if not isinstance(findings, list):
        return items
    for finding in findings[:50]:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity", "INFO")).upper()
        target = str(finding.get("target", "local-system"))
        desc = str(finding.get("description", "Defensive finding"))
        material = f"{severity}|{target}|{desc}".encode("utf-8", errors="replace")
        case_id = "INV-" + hashlib.sha256(material).hexdigest()[:8].upper()
        items.append(
            {
                "id": case_id,
                "severity": severity,
                "target": target,
                "title": desc[:100],
                "description": desc,
                "recommendation": str(finding.get("recommendation", "Analyst review")),
                "status": "ANALYST_REVIEW" if severity in {"HIGH", "CRITICAL"} else "OBSERVE",
                "source": "ZYRAPALANTIR LIVE",
                "human_authorization_required": True,
                "automatic_external_action": False,
            }
        )
    return items


def proposals(state: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for inv in investigations(state):
        out.append(
            {
                "id": "PROP-" + inv["id"].split("-", 1)[-1],
                "severity": inv["severity"],
                "title": f"Review {inv['target']}",
                "proposal": inv["recommendation"],
                "decision": "PENDING HUMAN REVIEW",
                "external_action": False,
            }
        )
    if not out:
        out.append(
            {
                "id": "PROP-BASELINE",
                "severity": "INFO",
                "title": "Maintain defensive baseline",
                "proposal": "Continue monitoring and preserve the current approved defensive configuration.",
                "decision": "INFORMATIONAL",
                "external_action": False,
            }
        )
    return out


def audit_events(limit: int = 40) -> list[dict[str, Any]]:
    combined = _tail_jsonl(getattr(field, "FIELD_AUDIT", STATE_DIR / "zyrapalantir-field-audit.jsonl"), limit)
    combined += _tail_jsonl(LIVE_AUDIT, limit)
    combined.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return combined[:limit]


def assistant_reply(prompt: str, state: dict[str, Any]) -> str:
    text = prompt.lower().strip()
    if not text:
        return "Ask about readiness, cyber findings, communications, assets, incidents, investigations, proposals, or audit history."
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
    if any(k in text for k in ("investigation", "case")):
        inv = investigations(state)
        return f"There are {len(inv)} local defensive investigation records derived from current findings. External response remains human-authorized."
    if any(k in text for k in ("proposal", "recommend")):
        p = proposals(state)
        return f"There are {len(p)} defensive recommendations available for analyst review. None execute external actions automatically."
    if "audit" in text:
        events = audit_events(40)
        return f"The local audit view currently exposes {len(events)} recent ZYRAPALANTIR events from private JSONL logs."
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
    return "I can summarize readiness, cyber findings, communications, assets, incidents, investigations, proposals, and audit history from the local ZYRAPALANTIR state."


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: Any, status: int = 200) -> None:
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
        state = None
        if parsed.path == "/api/state":
            self._json(field.snapshot(None))
            return
        if parsed.path == "/api/assistant":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            state = field.snapshot(None)
            self._json({"reply": assistant_reply(q, state), "state_timestamp": state.get("timestamp")})
            return
        if parsed.path == "/api/investigations":
            state = field.snapshot(None)
            self._json({"items": investigations(state), "timestamp": state.get("timestamp")})
            return
        if parsed.path == "/api/proposals":
            state = field.snapshot(None)
            self._json({"items": proposals(state), "timestamp": state.get("timestamp")})
            return
        if parsed.path == "/api/audit":
            self._json({"items": audit_events(40)})
            return
        if parsed.path in ("/", "/index.html"):
            self._file(WEB_ROOT / "index.html", "text/html; charset=utf-8")
            return
        self.send_error(404)

    def log_message(self, fmt: str, *args: Any) -> None:
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
    print("🎖️ ZYRAPALANTIR VISUAL FIELD OPS v2")
    print("🧠 interactive investigations + readiness + audit + analyst summaries")
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
