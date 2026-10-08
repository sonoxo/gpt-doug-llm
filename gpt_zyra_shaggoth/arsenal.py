"""Local-only visual defensive arsenal for GPT-ZYRA-Shaggoth.

This module visualizes defensive posture and lets a local operator submit text
through the existing Golden Shield inspection boundary. It does not scan remote
systems, execute containment actions, or expose an external control plane.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import webbrowser
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from golden_shield import GoldenShield

from .bridge import ZyraShaggothBridge
from .nexus import build_nexus_snapshot, load_local_brain, load_local_swarm, nexus_page

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GPT-ZYRA // Defensive Arsenal</title>
<style>
:root{
  color-scheme:dark;
  font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --bg:#02050a;--panel:#07111c;--panel2:#0a1724;--line:#17344a;--cyan:#50e3ff;
  --green:#63f5a5;--amber:#ffd166;--red:#ff647c;--text:#e7f8ff;--muted:#7fa3b7;
}
*{box-sizing:border-box}
body{
  margin:0;min-height:100vh;color:var(--text);
  background:
    linear-gradient(rgba(5,18,28,.72),rgba(2,5,10,.96)),
    repeating-linear-gradient(0deg,transparent 0 29px,rgba(80,227,255,.045) 30px),
    repeating-linear-gradient(90deg,transparent 0 29px,rgba(80,227,255,.045) 30px),
    radial-gradient(circle at 50% -10%,#103c51 0,#02050a 48%);
}
header{
  display:flex;justify-content:space-between;gap:20px;align-items:center;
  padding:22px 28px;border-bottom:1px solid var(--line);background:#030a12e8;position:sticky;top:0;z-index:3;
}
.brand{letter-spacing:.18em;font-weight:900;font-size:18px}.brand b{color:var(--cyan)}
.mode{font-size:11px;letter-spacing:.16em;color:var(--green);border:1px solid #1c6c4d;padding:7px 10px;border-radius:999px}
main{padding:22px;max-width:1500px;margin:auto}
.hero{display:grid;grid-template-columns:minmax(270px,.75fr) minmax(500px,1.6fr);gap:18px;margin-bottom:18px}
.panel{background:linear-gradient(180deg,#081521e8,#050c14e8);border:1px solid var(--line);border-radius:16px;box-shadow:0 16px 60px #0008}
.shield{min-height:370px;display:grid;place-items:center;position:relative;overflow:hidden}
.radar{position:relative;width:275px;height:275px;border-radius:50%;border:1px solid #1d7085;box-shadow:0 0 60px #00d9ff26 inset,0 0 55px #00d9ff16}
.radar:before,.radar:after{content:"";position:absolute;inset:17%;border:1px solid #1b5368;border-radius:50%}
.radar:after{inset:34%}
.cross-h,.cross-v{position:absolute;background:#1a5265}.cross-h{height:1px;width:100%;top:50%}.cross-v{width:1px;height:100%;left:50%}
.sweep{position:absolute;width:50%;height:50%;left:50%;top:0;transform-origin:0 100%;background:linear-gradient(135deg,rgba(80,227,255,.28),transparent 65%);animation:sweep 5s linear infinite}
@keyframes sweep{to{transform:rotate(360deg)}}
.core{position:absolute;inset:39%;display:grid;place-items:center;border:1px solid #62f5a5;border-radius:18px;transform:rotate(45deg);box-shadow:0 0 24px #63f5a54a}
.core span{transform:rotate(-45deg);font-weight:900;color:var(--green);font-size:11px;letter-spacing:.1em;text-align:center}
.hero-info{padding:24px}
.kicker{font-size:11px;color:var(--cyan);letter-spacing:.18em}.hero-info h1{font-size:36px;line-height:1.04;margin:8px 0 12px}
.hero-info p{color:var(--muted);max-width:780px;line-height:1.55}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:20px}
.metric{border:1px solid var(--line);background:#06101a;padding:14px;border-radius:12px}
.metric .v{font-size:27px;font-weight:900;color:var(--cyan)}.metric .l{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.09em}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}
.section{padding:18px}.section h2{margin:0 0 14px;font-size:13px;letter-spacing:.14em;color:#bcefff}
.layers{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.layer{padding:15px;border:1px solid var(--line);border-radius:12px;background:#06101a}
.layer-top{display:flex;justify-content:space-between;gap:8px}.layer-name{font-weight:800;font-size:13px}.state{font-size:10px;color:var(--green);letter-spacing:.1em}
.layer p{font-size:12px;color:var(--muted);line-height:1.45;margin:8px 0 0}
.sequence{display:grid;gap:8px}
.seq{display:grid;grid-template-columns:30px 1fr;align-items:center;gap:10px;padding:10px;border-left:2px solid #1f7187;background:#06101a}
.seq i{font-style:normal;color:var(--cyan);font-size:11px}.seq b{font-size:12px;letter-spacing:.08em}
.inspector{margin-top:18px;padding:18px}
.row{display:flex;gap:10px}.row textarea{flex:1;min-height:92px;resize:vertical;background:#02070d;color:var(--text);border:1px solid #24485e;border-radius:10px;padding:12px;font:inherit}
button{background:#0a5063;color:white;border:1px solid #2ca8bd;border-radius:10px;padding:0 18px;font-weight:800;cursor:pointer}
button:hover{background:#0d687e}.result{margin-top:12px;padding:13px;border-radius:10px;border:1px solid var(--line);background:#040b12;min-height:52px;white-space:pre-wrap;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.good{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}
.events{max-height:300px;overflow:auto;display:grid;gap:7px}
.event{padding:10px;border:1px solid var(--line);border-radius:10px;background:#040b12;font:11px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}
.boundary{font-size:11px;color:var(--muted);padding-top:12px;border-top:1px solid var(--line);margin-top:14px}
@media(max-width:900px){.hero,.grid{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}.layers{grid-template-columns:1fr}.shield{min-height:320px}}
</style>
</head>
<body>
<header>
  <div class="brand">GPT-ZYRA // <b>DEFENSIVE ARSENAL</b></div>
  <div class="mode">LOCAL • DEFENSIVE ONLY • HUMAN CONTROL</div>
</header>
<main>
  <section class="hero">
    <div class="panel shield">
      <div class="radar">
        <div class="cross-h"></div><div class="cross-v"></div><div class="sweep"></div>
        <div class="core"><span>GOLDEN<br/>SHIELD</span></div>
      </div>
    </div>
    <div class="panel hero-info">
      <div class="kicker">GPT-DOUG HARDWIRED DEFENSE PLANE</div>
      <h1>See the boundary.<br/>Verify the boundary.</h1>
      <p>This local operator view combines Golden Shield telemetry, tamper-evident mission state, private-key checks, and defensive incident readiness. It does not counter-hack, target external systems, or execute autonomous containment.</p>
      <div class="metrics">
        <div class="metric"><div id="health" class="v">—</div><div class="l">controls healthy</div></div>
        <div class="metric"><div id="blocked" class="v">0</div><div class="l">blocked</div></div>
        <div class="metric"><div id="quarantined" class="v">0</div><div class="l">quarantined</div></div>
        <div class="metric"><div id="integrity" class="v">—</div><div class="l">journal integrity</div></div>
      </div>
    </div>
  </section>

  <section class="grid">
    <div class="panel section">
      <h2>DEFENSE LAYERS</h2>
      <div id="layers" class="layers"></div>
    </div>
    <div class="panel section">
      <h2>INCIDENT SEQUENCE</h2>
      <div id="sequence" class="sequence"></div>
      <div class="boundary">Operator actions remain advisory and separately authorized. External effects are denied by the hardened Shaggoth bridge.</div>
    </div>
  </section>

  <section class="panel inspector">
    <h2>GOLDEN SHIELD LOCAL INSPECTOR</h2>
    <div class="row">
      <textarea id="probe" maxlength="8192" placeholder="Paste an inbound text sample to classify through the local Golden Shield boundary."></textarea>
      <button id="inspect">INSPECT</button>
    </div>
    <div id="result" class="result">No sample inspected.</div>
  </section>

  <section class="grid" style="margin-top:18px">
    <div class="panel section">
      <h2>RECENT LOCAL ASSESSMENTS</h2>
      <div id="events" class="events"></div>
    </div>
    <div class="panel section">
      <h2>BOUNDARY STATUS</h2>
      <div id="boundary" class="result"></div>
    </div>
  </section>
</main>
<script>
const esc=(v)=>String(v??"");
function addText(parent,tag,text,cls){const e=document.createElement(tag);if(cls)e.className=cls;e.textContent=text;parent.appendChild(e);return e}
async function refresh(){
  const s=await fetch("/api/status",{cache:"no-store"}).then(r=>r.json());
  health.textContent=s.summary.healthy_controls+"/"+s.summary.total_controls;
  blocked.textContent=s.shield.stats.blocked;
  quarantined.textContent=s.shield.stats.quarantined;
  integrity.textContent=s.bridge.checks.journal_chain_valid?"VERIFIED":"FAIL";
  integrity.className="v "+(s.bridge.checks.journal_chain_valid?"good":"bad");
  layers.replaceChildren();
  for(const x of s.layers){
    const card=document.createElement("div");card.className="layer";
    const top=document.createElement("div");top.className="layer-top";
    addText(top,"span",x.name,"layer-name");addText(top,"span",x.state,"state");
    card.appendChild(top);addText(card,"p",x.detail);layers.appendChild(card);
  }
  sequence.replaceChildren();
  s.incident_sequence.forEach((x,i)=>{const row=document.createElement("div");row.className="seq";addText(row,"i",String(i+1).padStart(2,"0"));addText(row,"b",x);sequence.appendChild(row)});
  boundary.textContent=JSON.stringify({
    system:s.system,mode:s.mode,network_actions:s.boundary.network_actions,
    external_effects:s.boundary.external_effects,remote_console:s.boundary.remote_console,
    repository_bound:s.bridge.checks.repository_bound_to_gpt_doug,
    keys_private:s.bridge.checks.journal_key_private&&s.bridge.checks.attestation_key_private
  },null,2);
  events.replaceChildren();
  if(!s.recent.length){addText(events,"div","No local assessments yet.","event")}
  s.recent.forEach(x=>{const e=document.createElement("div");e.className="event";e.textContent=`[${x.risk_level}] ${x.action} • ${x.classification} • ${x.timestamp}`;events.appendChild(e)});
}
inspect.addEventListener("click",async()=>{
  const text=probe.value.trim();if(!text){result.textContent="Enter a sample first.";return}
  result.textContent="Inspecting locally…";
  const r=await fetch("/api/inspect",{method:"POST",headers:{"Content-Type":"application/json","X-Doug-Client":"defensive-arsenal"},body:JSON.stringify({text})});
  const d=await r.json();
  result.textContent=JSON.stringify(d,null,2);
  result.className="result "+(d.action==="ALLOW"?"good":d.action==="QUARANTINE"?"warn":"bad");
  await refresh();
});
refresh();setInterval(refresh,2500);
</script>
</body>
</html>"""


class DefensiveArsenal:
    """Read-only defensive posture model backed by existing GPT-DOUG controls."""

    SYSTEM = "GPT-ZYRA-DEFENSIVE-ARSENAL"
    MODE = "LOCAL_DEFENSE_VISUAL"

    def __init__(self, bridge: ZyraShaggothBridge) -> None:
        self.bridge = bridge
        self.state_dir = bridge.state_dir
        key_path = self.state_dir / "arsenal-shield.key"
        self._reject_symlink(key_path)
        if key_path.exists():
            key = key_path.read_bytes()
            if len(key) < 32:
                raise RuntimeError("arsenal shield key is invalid")
        else:
            key = secrets.token_bytes(32)
            key_path.write_bytes(key)
            try:
                key_path.chmod(0o600)
            except OSError:
                pass
        self.shield = GoldenShield(
            audit_path=self.state_dir / "arsenal-shield-audit.jsonl",
            audit_key=key,
            strict=True,
        )
        self._recent: deque[dict[str, Any]] = deque(maxlen=30)
        self._lock = threading.Lock()

    @staticmethod
    def _reject_symlink(path: Path) -> None:
        if path.exists() and path.is_symlink():
            raise ValueError("defensive arsenal state must not use symlinked key material")

    def snapshot(self) -> dict[str, Any]:
        bridge = self.bridge.verify()
        shield = self.shield.status()
        checks = bridge["checks"]
        control_checks = {
            "gpt_doug_binding": bool(checks["repository_bound_to_gpt_doug"]),
            "journal_integrity": bool(checks["journal_chain_valid"]),
            "state_private": bool(checks["state_directory_private"]),
            "journal_key_private": bool(checks["journal_key_private"]),
            "attestation_key_private": bool(checks["attestation_key_private"]),
            "external_delivery_denied": bool(checks["github_delivery_denied"]),
            "network_provider_denied": bool(checks["network_provider_denied"]),
            "remote_console_disabled": bool(checks["remote_console_disabled"]),
            "golden_shield_strict": bool(shield["strict_mode"]),
        }
        healthy = sum(1 for value in control_checks.values() if value)
        layers = [
            {
                "id": "perimeter",
                "name": "PERIMETER",
                "state": "ONLINE" if shield["strict_mode"] else "DEGRADED",
                "detail": "Golden Shield inbound quarantine, rate containment, output sterilization, and tamper-evident audit boundary.",
            },
            {
                "id": "identity",
                "name": "IDENTITY + KEYS",
                "state": "VERIFIED" if checks["journal_key_private"] and checks["attestation_key_private"] else "CHECK",
                "detail": "Local journal and attestation signing material is checked for private file permissions.",
            },
            {
                "id": "integrity",
                "name": "INTEGRITY",
                "state": "VERIFIED" if checks["journal_chain_valid"] else "ALERT",
                "detail": "Mission history is hash-chained and locally signed so silent event editing is detectable.",
            },
            {
                "id": "detection",
                "name": "DETECTION",
                "state": "READY",
                "detail": "Local inspection classifies suspicious input without initiating remote scanning or counter-access.",
            },
            {
                "id": "containment",
                "name": "CONTAINMENT",
                "state": "HUMAN-GATED",
                "detail": "The bridge denies external effects; real containment remains a separately authorized operator action.",
            },
            {
                "id": "recovery",
                "name": "RECOVERY",
                "state": "READY",
                "detail": "Evidence, checkpoints, signed attestations, and known-good restore workflows remain visible for recovery decisions.",
            },
        ]
        with self._lock:
            recent = list(reversed(self._recent))
        return {
            "system": self.SYSTEM,
            "mode": self.MODE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "healthy_controls": healthy,
                "total_controls": len(control_checks),
                "defensive_only": True,
            },
            "boundary": {
                "localhost_only": True,
                "network_actions": False,
                "external_effects": False,
                "remote_console": False,
                "counter_hacking": False,
                "autonomous_containment": False,
            },
            "bridge": bridge,
            "shield": {
                "shield_version": shield["shield_version"],
                "zyra_version": shield["zyra_version"],
                "strict_mode": shield["strict_mode"],
                "stats": shield["stats"],
                "threat_fingerprints": shield["threat_fingerprints"],
                "rate_limit": shield["rate_limit"],
                "flood_threshold": shield["flood_threshold"],
            },
            "layers": layers,
            "control_checks": control_checks,
            "incident_sequence": [
                "IDENTIFY",
                "CONTAIN",
                "PRESERVE",
                "ERADICATE",
                "RECOVER",
                "REPORT",
                "LEARN",
            ],
            "recent": recent,
        }

    def inspect_text(self, text: str) -> dict[str, Any]:
        clean = str(text)
        if not clean.strip():
            raise ValueError("text is required")
        if len(clean) > 8192:
            raise ValueError("inspection input exceeds 8192 characters")
        assessment = self.shield.inspect_inbound(clean, source="defensive-arsenal-local")
        verdict = assessment.zyra_verdict
        result = {
            "timestamp": assessment.timestamp,
            "action": assessment.action,
            "risk_level": assessment.risk_level,
            "classification": assessment.classification,
            "rate_limited": assessment.rate_limited,
            "requires_approval": bool(verdict.requires_approval) if verdict is not None else False,
            "reason": assessment.reason,
            "signal_count": len(assessment.threat_signals) + len(assessment.rice_signals),
            "defensive_only": True,
        }
        with self._lock:
            self._recent.append(result)
        return result


class DefensiveArsenalServer:
    """Localhost-only HTTP server for the defensive visual arsenal."""

    def __init__(self, arsenal: DefensiveArsenal) -> None:
        self.arsenal = arsenal

    def serve(self, *, port: int = 8791, open_nexus: bool = False) -> None:
        chosen = int(port)
        if not (1024 <= chosen <= 65535):
            raise ValueError("arsenal port must be between 1024 and 65535")
        arsenal = self.arsenal

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _fmt: str, *_args: object) -> None:
                return

            def _headers(self, status: int, content_type: str, length: int) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
                    "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                )
                self.end_headers()

            def _json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
                self._headers(status, "application/json; charset=utf-8", len(body))
                self.wfile.write(body)

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/":
                    body = HTML.encode("utf-8")
                    self._headers(200, "text/html; charset=utf-8", len(body))
                    self.wfile.write(body)
                    return
                if path == "/api/status":
                    self._json(200, arsenal.snapshot())
                    return
                if path == "/nexus":
                    body = nexus_page().encode("utf-8")
                    self._headers(200, "text/html; charset=utf-8", len(body))
                    self.wfile.write(body)
                    return
                if path == "/api/nexus":
                    try:
                        payload = build_nexus_snapshot(
                            arsenal.snapshot(),
                            brain=load_local_brain(),
                            swarm=load_local_swarm(),
                        )
                    except ValueError:
                        self._json(503, {"error": "hardened boundary verification failed"})
                        return
                    self._json(200, payload)
                    return
                self._json(404, {"error": "not found"})

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                if path != "/api/inspect":
                    self._json(404, {"error": "not found"})
                    return
                if self.headers.get("X-Doug-Client") != "defensive-arsenal":
                    self._json(403, {"error": "local arsenal client header required"})
                    return
                try:
                    declared = int(self.headers.get("Content-Length", "0") or 0)
                except ValueError:
                    self._json(400, {"error": "invalid content length"})
                    return
                if declared < 1 or declared > 12288:
                    self._json(413, {"error": "request too large"})
                    return
                try:
                    payload = json.loads(self.rfile.read(declared))
                    result = arsenal.inspect_text(str(payload.get("text", "")))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._json(400, {"error": "invalid json"})
                    return
                except ValueError as exc:
                    self._json(400, {"error": str(exc)})
                    return
                self._json(200, result)

        server = ThreadingHTTPServer(("127.0.0.1", chosen), Handler)
        address = f"http://127.0.0.1:{chosen}"
        browser_address = f"{address}/nexus" if open_nexus else address
        print(f"GPT-ZYRA Defensive Arsenal: {address}", flush=True)
        # Open the local HUD when launched interactively on macOS.
        # CI and headless operators can disable the browser explicitly.
        if sys.platform == "darwin" and not os.environ.get("CI") and os.environ.get("ZYRA_ARSENAL_NO_BROWSER") != "1":
            try:
                webbrowser.open(browser_address, new=2)
            except (OSError, webbrowser.Error):
                print(f"Open manually in your browser: {address}", flush=True)
        server.serve_forever()


def serve_defensive_arsenal(
    bridge: ZyraShaggothBridge,
    *,
    port: int = 8791,
    open_nexus: bool = False,
) -> None:
    """Run the defensive arsenal on loopback only."""

    if os.environ.get("ZYRA_ALLOW_REMOTE_ARSENAL"):
        raise PermissionError("remote defensive arsenal binding is not supported")
    DefensiveArsenalServer(DefensiveArsenal(bridge)).serve(port=port, open_nexus=open_nexus)
