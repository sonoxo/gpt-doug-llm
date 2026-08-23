"""Local-only ZYRA Mission Control web console."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .control_plane import MissionControl

HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>ZYRA Mission Control</title><style>
:root{color-scheme:dark;font-family:Inter,system-ui,sans-serif;background:#050816;color:#e8f7ff}body{margin:0;background:radial-gradient(circle at 50% 0,#17134c 0,#050816 45%);min-height:100vh}header{padding:28px 32px;border-bottom:1px solid #1d4ed8;background:#071024cc;position:sticky;top:0}h1{margin:0;color:#dffcff;letter-spacing:.08em}.sub{color:#67e8f9;margin-top:6px}main{padding:24px;display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}.card{border:1px solid #164e63;border-radius:16px;background:#07111ecc;padding:18px;box-shadow:0 0 30px #0891b222}.card h2{color:#a78bfa;margin-top:0;font-size:16px;text-transform:uppercase;letter-spacing:.08em}.metric{font-size:30px;font-weight:800;color:#67e8f9}.ok{color:#34d399}.bad{color:#fb7185}table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #18324d;text-align:left}pre{white-space:pre-wrap;max-height:400px;overflow:auto;background:#020617;padding:12px;border-radius:10px}button{background:#4f46e5;color:white;border:0;padding:10px 14px;border-radius:9px;cursor:pointer;margin-right:8px}input{background:#020617;color:#e8f7ff;border:1px solid #334155;padding:10px;border-radius:8px}.full{grid-column:1/-1}
</style></head><body>
<header><h1>GPT-DOUG + ZYRA MISSION CONTROL</h1><div class="sub">Journal • DAG • Capabilities • Sandbox • Attestations • Benchmarks</div></header>
<main>
<section class="card"><h2>Journal integrity</h2><div id="journal" class="metric">...</div><div id="eventCount"></div></section>
<section class="card"><h2>Artifacts</h2><div>Checkpoints <b id="checkpoints">0</b></div><div>Attestations <b id="attestations">0</b></div></section>
<section class="card"><h2>Capabilities</h2><div class="metric" id="capCount">0</div><div>registered agents/tools</div></section>
<section class="card"><h2>Telemetry</h2><div>Model calls <b id="modelCalls">0</b></div><div>Tokens <b id="tokens">0</b></div><div>Runtime <b id="runtime">0 ms</b></div></section>
<section class="card"><h2>Reliability benchmark</h2><div class="metric" id="benchScore">N/A</div><div id="benchMeta">No scorecard yet.</div></section>
<section class="card"><h2>Runtime</h2><pre id="ecosystem">Loading...</pre></section>
<section class="card"><h2>Latest DAG plan</h2><pre id="plan">No plan yet.</pre></section>
<section class="card full"><h2>Capability registry</h2><table><thead><tr><th>Name</th><th>Kind</th><th>Capabilities</th><th>Boundary</th></tr></thead><tbody id="caps"></tbody></table></section>
<section class="card full"><h2>Mission history</h2><table><thead><tr><th>Mission</th><th>Goal</th><th>Events</th><th>Last state</th></tr></thead><tbody id="missions"></tbody></table></section>
<section class="card full"><h2>Live mission events</h2><pre id="events">No events yet.</pre></section>
<section class="card full"><h2>Diff previews</h2><pre id="diffs">No diff previews yet.</pre></section>
<section class="card full"><h2>Operator control requests</h2><input id="mission" placeholder="mission id" maxlength="32"/><button onclick="requestControl('checkpoint')">Request checkpoint</button><button onclick="requestControl('rollback')">Request rollback</button><span id="controlResult"></span></section>
</main><script>
function esc(x){return String(x).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
async function refresh(){
 const s=await fetch('/api/status').then(r=>r.json());journal.textContent=s.journal.ok?'VERIFIED':'BROKEN';journal.className='metric '+(s.journal.ok?'ok':'bad');eventCount.textContent=s.journal.events+' signed events';checkpoints.textContent=s.checkpoints;attestations.textContent=s.attestations;capCount.textContent=s.capabilities.length;caps.innerHTML=s.capabilities.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.kind)}</td><td>${x.capabilities.map(esc).join(', ')}</td><td>${x.network?'network ':''}${x.writes?'write ':''}${x.external_effects?'external':''}</td></tr>`).join('');
 const e=await fetch('/api/events').then(r=>r.json());events.textContent=e.events.length?e.events.map(x=>`${x.sequence} ${x.event} [${x.mission_id}]`).join('\n'):'No events yet.';
 const t=await fetch('/api/telemetry').then(r=>r.json());modelCalls.textContent=t.model_calls;tokens.textContent=t.input_tokens+t.output_tokens;runtime.textContent=t.duration_ms_total+' ms';
 const m=await fetch('/api/missions').then(r=>r.json());missions.innerHTML=m.missions.map(x=>`<tr><td>${esc(x.mission_id)}</td><td>${esc(x.goal||'')}</td><td>${x.events}</td><td>${esc(x.last_event||'')}</td></tr>`).join('');
 const b=await fetch('/api/benchmark').then(r=>r.json());benchScore.textContent=b.available?b.score:'N/A';benchMeta.textContent=b.available?`verified ${Math.round((b.verified_rate||0)*100)}% • false-success ${Math.round((b.false_success_rate||0)*100)}%`:'No scorecard yet.';
 const d=await fetch('/api/diffs').then(r=>r.json());diffs.textContent=d.events.length?d.events.map(x=>JSON.stringify(x.data,null,2)).join('\n\n'):'No diff previews yet.';
 const p=await fetch('/api/plan').then(r=>r.json());plan.textContent=p.event?JSON.stringify(p.data,null,2):'No plan yet.';
 const eco=await fetch('/api/ecosystem').then(r=>r.json());ecosystem.textContent=JSON.stringify(eco,null,2);
}
async function requestControl(action){const mission_id=document.getElementById('mission').value.trim();const r=await fetch('/api/control/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-Doug-Client':'mission-console'},body:JSON.stringify({mission_id})});const d=await r.json();controlResult.textContent=d.ok?'request queued':'request rejected: '+(d.error||'unknown');}
refresh();setInterval(refresh,1500);
</script></body></html>"""


class MissionConsole:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.control = MissionControl(self.state_dir)
        self.requests = self.state_dir / "control-requests.jsonl"

    def events(self) -> list[dict[str, object]]:
        if not self.control.journal.path.exists():
            return []
        out = []
        for line in self.control.journal.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out[-250:]

    def mission_history(self) -> list[dict[str, object]]:
        missions: dict[str, dict[str, object]] = {}
        for event in self.events():
            mission_id = str(event.get("mission_id", ""))
            if not mission_id:
                continue
            item = missions.setdefault(mission_id, {"mission_id": mission_id, "events": 0, "last_event": None, "goal": None})
            item["events"] = int(item["events"]) + 1
            item["last_event"] = event.get("event")
            if event.get("event") == "MISSION_CREATED":
                item["goal"] = (event.get("data") or {}).get("goal")
        return list(reversed(list(missions.values())))

    def telemetry(self) -> dict[str, object]:
        events = self.events()
        model_calls = input_tokens = output_tokens = 0
        durations = []
        failures: dict[str, int] = {}
        for event in events:
            telemetry = event.get("telemetry") or {}
            model_calls += int(telemetry.get("model_calls") or 0)
            input_tokens += int(telemetry.get("input_tokens") or 0)
            output_tokens += int(telemetry.get("output_tokens") or 0)
            if telemetry.get("duration_ms") is not None:
                durations.append(int(telemetry["duration_ms"]))
            failure = event.get("failure_type")
            if failure:
                failures[str(failure)] = failures.get(str(failure), 0) + 1
        return {"model_calls": model_calls, "input_tokens": input_tokens, "output_tokens": output_tokens, "duration_ms_total": sum(durations), "failures": failures}

    def benchmark(self) -> dict[str, object]:
        path = self.state_dir / "benchmark-scorecard.json"
        if not path.exists():
            return {"available": False}
        try:
            return {"available": True, **json.loads(path.read_text(encoding="utf-8"))}
        except (OSError, json.JSONDecodeError):
            return {"available": False, "error": "invalid scorecard"}

    def diff_events(self) -> list[dict[str, object]]:
        return [event for event in self.events() if event.get("event") in {"PATCH_PREVIEW", "FILE_DIFF"}]

    def latest_plan(self) -> dict[str, object]:
        plans = [event for event in self.events() if event.get("event") == "PLAN_CREATED"]
        return plans[-1] if plans else {"available": False}

    def ecosystem_status(self) -> dict[str, object]:
        status: dict[str, object] = {}
        try:
            from zyra_laser import ZyraLaser
            status["laser"] = ZyraLaser().status()
        except Exception as exc:  # noqa: BLE001
            status["laser"] = {"available": False, "error": type(exc).__name__}
        try:
            from agents import llm_backend
            status["provider"] = llm_backend.health()
        except Exception as exc:  # noqa: BLE001
            status["provider"] = {"available": False, "error": type(exc).__name__}
        try:
            from zyra_self_heal import RUNTIME_ENV
            status["self_heal"] = {"runtime_env": str(RUNTIME_ENV), "configured": RUNTIME_ENV.exists(), "last_modified": RUNTIME_ENV.stat().st_mtime if RUNTIME_ENV.exists() else None}
        except Exception as exc:  # noqa: BLE001
            status["self_heal"] = {"available": False, "error": type(exc).__name__}
        return status

    def queue_request(self, action: str, mission_id: str) -> dict[str, object]:
        if action not in {"checkpoint", "rollback"}:
            return {"ok": False, "error": "unsupported control"}
        if not mission_id or len(mission_id) > 32:
            return {"ok": False, "error": "mission_id required"}
        record = {"action": action, "mission_id": mission_id, "status": "PENDING_OPERATOR_RUNTIME"}
        self.requests.parent.mkdir(parents=True, exist_ok=True)
        with self.requests.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.control.journal.append(mission_id, "CONTROL_REQUESTED", data={"action": action, "source": "mission-console"})
        return {"ok": True, **record}


def serve(state_dir: str | Path | None = None, *, host: str = "127.0.0.1", port: int = 8790) -> None:
    if host not in {"127.0.0.1", "localhost"} and os.environ.get("ZYRA_ALLOW_REMOTE_CONSOLE") != "1":
        raise PermissionError("remote Mission Control binding requires ZYRA_ALLOW_REMOTE_CONSOLE=1")
    console = MissionConsole(state_dir or Path.home() / ".gpt-doug" / "mission-control")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _fmt: str, *_args: object) -> None:
            return

        def _json(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                body = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            routes = {
                "/api/status": console.control.status,
                "/api/telemetry": console.telemetry,
                "/api/benchmark": console.benchmark,
                "/api/plan": console.latest_plan,
                "/api/ecosystem": console.ecosystem_status,
            }
            if path in routes:
                return self._json(200, routes[path]())
            if path == "/api/events":
                return self._json(200, {"events": console.events()})
            if path == "/api/missions":
                return self._json(200, {"missions": console.mission_history()})
            if path == "/api/diffs":
                return self._json(200, {"events": console.diff_events()})
            return self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if self.headers.get("X-Doug-Client") != "mission-console":
                return self._json(403, {"ok": False, "error": "control header required"})
            length = min(int(self.headers.get("Content-Length", "0") or 0), 4096)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"ok": False, "error": "invalid json"})
            prefix = "/api/control/"
            if path.startswith(prefix):
                action = path[len(prefix):]
                result = console.queue_request(action, str(payload.get("mission_id", "")))
                return self._json(200 if result["ok"] else 400, result)
            return self._json(404, {"ok": False, "error": "not found"})

    server = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"ZYRA Mission Control: http://{host}:{port}")
    server.serve_forever()
