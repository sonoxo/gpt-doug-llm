#!/usr/bin/env python3
"""Interactive loopback-only ZYRAPALANTIR field dashboard.

Provides local defensive state, real persisted Palantir Maven round-trip proof,
read-only investigations/proposals/audit views, and a governed local Maven
ontology control-map session. Ontology initiation activates visualization and
local audit state only; it does not write to Foundry or perform external actions.
"""
from __future__ import annotations

import argparse
import datetime as dt
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
ONTOLOGY_PATH = ROOT / "docs" / "maven-ontology" / "ontology.json"
ONTOLOGY_SESSION: dict[str, Any] = {"status": "STANDBY", "initiated_at": None}

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


def _append_audit(event: dict[str, Any]) -> None:
    path = getattr(field, "FIELD_AUDIT", STATE_DIR / "zyrapalantir-field-audit.jsonl")
    try:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
        path.chmod(0o600)
    except Exception:
        pass


def _load_ontology() -> dict[str, Any]:
    data = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Maven ontology must be a JSON object")
    nodes = data.get("nodes")
    links = data.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ValueError("Maven ontology requires nodes[] and links[]")
    node_ids = {n.get("id") for n in nodes if isinstance(n, dict) and n.get("id")}
    invalid_links = [x for x in links if not isinstance(x, list) or len(x) < 3 or x[0] not in node_ids or x[1] not in node_ids]
    if invalid_links:
        raise ValueError(f"Maven ontology has {len(invalid_links)} invalid connector(s)")
    return data


def ontology_payload() -> dict[str, Any]:
    data = _load_ontology()
    out = dict(data)
    out["session"] = dict(ONTOLOGY_SESSION)
    out["source_path"] = str(ONTOLOGY_PATH)
    out["external_action"] = False
    out["foundry_write"] = False
    return out


def initiate_ontology() -> dict[str, Any]:
    data = _load_ontology()
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    ONTOLOGY_SESSION.update({"status": "ACTIVE", "initiated_at": now})
    event = {
        "timestamp": now,
        "schema": "xunia.maven-ontology-control-map.v1",
        "action": "ontology_initiated",
        "ontology_id": (data.get("meta") or {}).get("id"),
        "node_count": len(data.get("nodes", [])),
        "link_count": len(data.get("links", [])),
        "local_control_map": True,
        "foundry_write": False,
        "automatic_external_action": False,
    }
    _append_audit(event)
    return {
        "ok": True,
        "initiated_at": now,
        "node_count": len(data.get("nodes", [])),
        "link_count": len(data.get("links", [])),
        "meta": data.get("meta", {}),
        "ontology": ontology_payload(),
        "foundry_write": False,
        "automatic_external_action": False,
    }


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
        items.append({
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
        })
    return items


def proposals(state: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for inv in investigations(state):
        out.append({
            "id": "PROP-" + inv["id"].split("-", 1)[-1],
            "severity": inv["severity"],
            "title": f"Review {inv['target']}",
            "proposal": inv["recommendation"],
            "decision": "PENDING HUMAN REVIEW",
            "external_action": False,
        })
    if not out:
        out.append({
            "id": "PROP-BASELINE",
            "severity": "INFO",
            "title": "Maintain defensive baseline",
            "proposal": "Continue monitoring and preserve the current approved defensive configuration.",
            "decision": "INFORMATIONAL",
            "external_action": False,
        })
    return out


def audit_events(limit: int = 40) -> list[dict[str, Any]]:
    combined = _tail_jsonl(getattr(field, "FIELD_AUDIT", STATE_DIR / "zyrapalantir-field-audit.jsonl"), limit)
    combined += _tail_jsonl(LIVE_AUDIT, limit)
    combined.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return combined[:limit]


def assistant_reply(prompt: str, state: dict[str, Any]) -> str:
    text = prompt.lower().strip()
    if not text:
        return "Ask about readiness, Maven proof, Maven ontology, cyber findings, communications, assets, incidents, investigations, proposals, or audit history."
    if "ontology" in text or "control map" in text:
        try:
            o = ontology_payload()
            meta = o.get("meta", {})
            session = o.get("session", {})
            return (
                f"Maven ontology {meta.get('id','unknown')} v{meta.get('version','unknown')} is {session.get('status','STANDBY')} "
                f"with {len(o.get('nodes', []))} objects and {len(o.get('links', []))} connectors. "
                "Initiation activates the local governed control map only; no Foundry write occurs."
            )
        except Exception as exc:
            return f"Maven ontology is unavailable: {exc}"
    if any(k in text for k in ("maven", "artifact", "sha", "hash", "provenance", "roundtrip", "round-trip")):
        p = state.get("maven_proof", {}) or {}
        if not p.get("coordinates"):
            return "No persisted real Maven round-trip proof is available yet. Run zyra-maven verify, then refresh this dashboard."
        pub, ret, integ = p.get("publish", {}), p.get("retrieve", {}), p.get("integrity", {})
        return (
            f"Real Maven proof: {p.get('coordinates')} on {p.get('host')}. "
            f"Publish POM/JAR={pub.get('pom_status')}/{pub.get('jar_status')}; "
            f"retrieve POM/JAR={ret.get('pom_status')}/{ret.get('jar_status')}; "
            f"POM match={bool(integ.get('pom_match'))}; JAR match={bool(integ.get('jar_match'))}; "
            f"defense_ready={bool(p.get('defense_ready'))}."
        )
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
            f"Current defensive findings: LOW={counts.get('LOW',0)}, MEDIUM={counts.get('MEDIUM',0)}, "
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
    if any(k in text for k in ("comms", "network", "link", "connector")):
        c = state.get("comms", {})
        return (
            f"Local defensive comms view: interface={c.get('default_route_interface','unknown')}; "
            f"addresses={', '.join(c.get('local_addresses', [])[:4]) or 'none'}. "
            "Connectors are inspectable model relationships; this console does not reconfigure or disrupt networks."
        )
    if any(k in text for k in ("asset", "host", "device")):
        a = state.get("local_asset", {})
        return f"Local asset: {a.get('hostname','unknown')} running {a.get('system','unknown')} {a.get('release','')} on {a.get('machine','unknown')}."
    if "incident" in text:
        return (
            "Analyst attention is "
            f"{'REQUIRED' if state.get('analyst_attention_required') else 'NOT CURRENTLY REQUIRED'}. "
            "Any external response remains human-authorized."
        )
    return "I can summarize readiness, real Maven proof, Maven ontology, cyber findings, communications, assets, incidents, investigations, proposals, and audit history."


def _index_html() -> bytes:
    return (WEB_ROOT / "index.html").read_bytes()


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _index(self) -> None:
        body = _index_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            self._json(field.snapshot(None))
            return
        if parsed.path == "/api/maven-proof":
            self._json(field.latest_maven_proof())
            return
        if parsed.path == "/api/ontology":
            try:
                self._json(ontology_payload())
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
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
            self._index()
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/ontology/initiate":
            try:
                self._json(initiate_ontology())
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)}, 500)
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
    _load_ontology()
    url = f"http://127.0.0.1:{args.port}/"
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("🎖️ ZYRAPALANTIR VISUAL FIELD OPS v4")
    print("📦 toggleable real Palantir Maven proof")
    print("🧠 governed Maven ontology control map + inspectable connectors")
    print("🔗 working menus, back navigation, nodes and connector details")
    print("🛰️ local defensive telemetry + human decision support")
    print("🗺️ right panel remains NON-GEOGRAPHIC")
    print("⛔ automatic external action: DISABLED")
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
