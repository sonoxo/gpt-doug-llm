#!/usr/bin/env python3
"""Interactive local browser dashboard for ZYRAPALANTIR field decision support.

The service binds to loopback only, visualizes local defensive state, exposes
read-only investigation/readiness/audit views, and surfaces the latest persisted
real Palantir Maven publish/retrieve/hash proof. It does not select targets,
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
        return "Ask about readiness, Maven proof, cyber findings, communications, assets, incidents, investigations, proposals, or audit history."
    if any(k in text for k in ("maven", "artifact", "sha", "hash", "provenance", "roundtrip", "round-trip")):
        p = state.get("maven_proof", {}) or {}
        if not p.get("coordinates"):
            return "No persisted real Maven round-trip proof is available yet. Run the Palantir Maven roundtrip command, then refresh this dashboard."
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
    return "I can summarize readiness, real Maven round-trip proof, cyber findings, communications, assets, incidents, investigations, proposals, and audit history."


def _index_html() -> bytes:
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    injection = r'''
<style>
#realMavenProof{position:absolute;right:18px;top:58px;z-index:6;width:min(470px,46vw);max-height:48vh;overflow:auto;background:#0d151bdd;border:1px solid #355468;border-radius:10px;padding:12px 14px;font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;box-shadow:0 10px 30px #0008}
#realMavenProof h3{margin:0 0 7px;font-size:12px;color:#e8eef4}#realMavenProof .good{color:#50d890}#realMavenProof .bad{color:#ee5b63}#realMavenProof .muted{color:#8fa2b5}#realMavenProof code{word-break:break-all;color:#d7e5ef}
</style>
<div id="realMavenProof"><h3>📦 PALANTIR MAVEN // REAL ROUND-TRIP PROOF</h3><div class="muted">Waiting for persisted proof…</div></div>
<script>
(function(){
 const el=document.getElementById('realMavenProof');
 const esc2=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 async function refreshMavenProof(){
  try{
   const r=await fetch('/api/maven-proof',{cache:'no-store'}); const p=await r.json();
   if(!p||!p.coordinates){el.innerHTML='<h3>📦 PALANTIR MAVEN // REAL ROUND-TRIP PROOF</h3><div class="bad">NO PERSISTED PROOF</div><div class="muted">Run: bash redpanda-desktop/palantir-maven roundtrip</div>';return;}
   const pub=p.publish||{},ret=p.retrieve||{},i=p.integrity||{}; const ok=!!(p.ok&&i.pom_match&&i.jar_match);
   el.innerHTML=`<h3>📦 PALANTIR MAVEN // REAL ROUND-TRIP PROOF</h3>
   <div class="${ok?'good':'bad'}">${ok?'✅ VERIFIED':'❌ FAILED'}</div>
   <div>Host: <code>${esc2(p.host)}</code></div>
   <div>Artifact: <code>${esc2(p.coordinates)}</code></div>
   <div>Verified: <code>${esc2(p.verified_at||'unknown')}</code></div>
   <hr style="border:0;border-top:1px solid #2d3b48">
   <div>⬆ PUBLISH — POM <b>${esc2(pub.pom_status)}</b> / JAR <b>${esc2(pub.jar_status)}</b></div>
   <div>⬇ RETRIEVE — POM <b>${esc2(ret.pom_status)}</b> / JAR <b>${esc2(ret.jar_status)}</b></div>
   <div>🔏 POM match: <b class="${i.pom_match?'good':'bad'}">${esc2(i.pom_match)}</b></div>
   <div>🔏 JAR match: <b class="${i.jar_match?'good':'bad'}">${esc2(i.jar_match)}</b></div>
   <div># POM SHA-256: <code>${esc2(i.pom_sha256||'n/a')}</code></div>
   <div># JAR SHA-256: <code>${esc2(i.jar_sha256||'n/a')}</code></div>
   <div>🛡 defense_ready: <b class="${p.defense_ready?'good':'bad'}">${esc2(p.defense_ready)}</b></div>
   <div>🔐 credentials stored/printed: false/false</div>`;
  }catch(e){el.innerHTML='<h3>📦 PALANTIR MAVEN // REAL ROUND-TRIP PROOF</h3><div class="bad">Proof API unavailable: '+esc2(e.message)+'</div>'}
 }
 refreshMavenProof(); setInterval(refreshMavenProof,3000);
})();
</script>
'''
    return html.replace("</body>", injection + "\n</body>").encode("utf-8")


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
        state = None
        if parsed.path == "/api/state":
            self._json(field.snapshot(None))
            return
        if parsed.path == "/api/maven-proof":
            self._json(field.latest_maven_proof())
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
    print("🎖️ ZYRAPALANTIR VISUAL FIELD OPS v3")
    print("📦 real Palantir Maven round-trip proof + live readiness")
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
