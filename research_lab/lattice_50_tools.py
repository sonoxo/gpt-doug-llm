"""50 offline Lattice-inspired developer tools over synthetic Kraken data.

The outputs are NOT Lattice API payloads. No network calls, publishing, task
execution, robot control, or video collection. Python standard library only.

python3 -m research_lab.lattice_50_tools list
python3 -m research_lab.lattice_50_tools run entities.health --agents 100 --ticks 20
python3 -m research_lab.lattice_50_tools serve --port 8765
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import json
import os
from urllib.parse import parse_qs, urlparse

from research_lab.kraken_lattice_preview import make_snapshot
from research_lab.kraken_robot_sim import MAX_AGENTS, MAX_TICKS, ROLES

DOCS = {
    "index": "https://developer.anduril.com/llms.txt",
    "entities": "https://developer.anduril.com/guides/entities/overview",
    "tasks": "https://developer.anduril.com/guides/tasks/overview",
    "objects": "https://developer.anduril.com/guides/objects/overview",
    "video": "https://developer.anduril.com/guides/video/overview",
    "sdk": "https://developer.anduril.com/guides/getting-started/set-up",
    "sandboxes": "https://developer.anduril.com/guides/developer-tools/sandboxes",
    "python_sdk": "https://github.com/anduril/lattice-sdk-python",
}
STATUSES = ("queued", "in_progress", "completed")  # Local labels, not Lattice enums.


def dataset(agents: int = 16, ticks: int = 20) -> dict:
    if not 1 <= agents <= MAX_AGENTS or not 1 <= ticks <= MAX_TICKS:
        raise ValueError(f"agents must be 1..{MAX_AGENTS}; ticks must be 1..{MAX_TICKS}")
    snapshot = make_snapshot(agents, ticks)
    entities = [
        {"id": e["external_id"], "role": e["role"], "battery": e["battery_percent"],
         "x": e["grid_position"]["x"], "y": e["grid_position"]["y"],
         "source": "kraken-local-sim", "synthetic": True, "last_tick": ticks}
        for e in snapshot["entity_previews"]
    ]
    tasks = [
        {"id": f"support-task-{i:03d}", "entity_id": e["id"], "role": e["role"],
         "description": f"Synthetic {e['role']} workflow", "status": STATUSES[i % 3],
         "due_tick": ticks + i + 1, "synthetic": True}
        for i, e in enumerate(entities)
    ]
    objects = []
    for i, e in enumerate(entities):
        body = json.dumps({"entity_id": e["id"], "role": e["role"]}, sort_keys=True)
        objects.append({"id": f"sim/manifest-{i:03d}.json", "kind": "application/json",
                        "size_bytes": len(body.encode()), "sha256": hashlib.sha256(body.encode()).hexdigest(),
                        "expires_tick": ticks + 10 + i, "synthetic": True})
    streams = [
        {"id": f"virtual-video-{i:03d}", "entity_id": e["id"],
         "status": ("STREAM_STATUS_LIVE" if i % 3 else "STREAM_STATUS_INACTIVE"),
         "protocol": "synthetic", "width": (640 if i % 2 else 1280), "height": (480 if i % 2 else 720),
         "fps": (10 if i % 2 else 15), "bitrate_kbps": (350 if i % 2 else 900),
         "last_frame_tick": ticks - (i % 4), "synthetic": True}
        for i, e in enumerate(entities)
    ]
    return {"entities": entities, "tasks": tasks, "objects": objects, "video": streams,
            "snapshot": snapshot, "agents": agents, "ticks": ticks,
            "sampled": len(entities), "omitted": agents - len(entities)}


def lookup(items: list[dict], identity: str) -> dict | None:
    return next((r for r in items if r["id"] == identity), None)


def tally(items: list[dict], key: str) -> dict:
    return dict(sorted(Counter(r[key] for r in items).items()))


def validate_entities(s: dict) -> dict:
    failures = [e["id"] for e in s["entities"] if not (e["id"] and e["synthetic"]
                 and e["source"] and 0 <= e["battery"] <= 100 and 0 <= e["x"] < 64 and 0 <= e["y"] < 64)]
    return {"valid": not failures, "failures": failures, "scope": "local synthetic preview only"}


def validate_tasks(s: dict) -> dict:
    failures = [t["id"] for t in s["tasks"] if not (t["description"] and t["entity_id"] and t["status"] in STATUSES)]
    return {"valid": not failures, "failures": failures, "schema": "local synthetic workflow"}


def validate_objects(s: dict) -> dict:
    failures = [o["id"] for o in s["objects"] if not (0 <= o["size_bytes"] < 2**30 and len(o["sha256"]) == 64)]
    return {"valid": not failures, "failures": failures, "size_cap_bytes": 2**30 - 1}


def validate_video(s: dict) -> dict:
    failures = [v["id"] for v in s["video"] if not (v["synthetic"] and v["fps"] > 0 and v["width"] > 0 and v["height"] > 0)]
    return {"valid": not failures, "failures": failures, "frames_present": False}


def get_or_first(s: dict, category: str, identity: str) -> dict | None:
    return lookup(s[category], identity or s[category][0]["id"]) if s[category] else None


def sample_group_by_role(s: dict) -> dict:
    return tally(s["entities"], "role")


def full_role_counts(s: dict) -> dict:
    # The Kraken generator assigns roles round-robin to each virtual agent.
    return {role: s["agents"] // len(ROLES) + (int(i < s["agents"] % len(ROLES)))
            for i, role in enumerate(ROLES)}


def task_load(s: dict) -> dict:
    return dict(sorted(Counter(t["entity_id"] for t in s["tasks"]).items()))


def check_integrity(s: dict) -> dict:
    invalid = []
    for obj in s["objects"]:
        idx = int(obj["id"].split("-")[-1].split(".")[0])
        e = s["entities"][idx]
        body = json.dumps({"entity_id": e["id"], "role": e["role"]}, sort_keys=True).encode()
        if hashlib.sha256(body).hexdigest() != obj["sha256"] or len(body) != obj["size_bytes"]:
            invalid.append(obj["id"])
    return {"valid": not invalid, "invalid_ids": invalid, "verified_against": "deterministic synthetic metadata"}


def privacy_audit(s: dict) -> dict:
    encoded = json.dumps({k: s[k] for k in ("entities", "tasks", "objects", "video")}).lower()
    indicators = ("client_secret", "bearer ", "private_key", "access_token", "password")
    return {"credentials_in_synthetic_records": any(x in encoded for x in indicators),
            "real_person_data": False, "mode": "offline"}


def tool(name: str, desc: str, fn):
    TOOLS[name] = (desc, fn)


TOOLS = {}
# ENTITY tools: all act on sampled local entities; totals are labeled explicitly.
tool("entities.list", "List synthetic preview entities", lambda s, a: s["entities"])
tool("entities.get", "Get a synthetic entity by --id", lambda s, a: get_or_first(s, "entities", a.id))
tool("entities.search", "Search entity IDs and roles", lambda s, a: [e for e in s["entities"] if a.query.casefold() in (e["id"] + e["role"]).casefold()])
tool("entities.count", "Count total robots and sampled entities", lambda s, a: {"total": s["agents"], "sampled": s["sampled"], "omitted": s["omitted"]})
tool("entities.roles", "Count roles across complete synthetic fleet", lambda s, a: full_role_counts(s))
tool("entities.validate", "Validate local entity fields and coordinate bounds", lambda s, a: validate_entities(s))
tool("entities.low_battery", "Filter sampled units at or below threshold", lambda s, a: [e for e in s["entities"] if e["battery"] <= a.threshold])
tool("entities.positions", "Read nongeographic synthetic grid positions", lambda s, a: [{"id": e["id"], "grid": [e["x"], e["y"]]} for e in s["entities"]])
tool("entities.health", "Summarize powered units across complete fleet", lambda s, a: {"powered": s["snapshot"]["health"]["powered_units"], "total": s["agents"], "ticks": s["ticks"]})
tool("entities.provenance", "List synthetic source identifiers", lambda s, a: [{"id": e["id"], "source": e["source"], "synthetic": True} for e in s["entities"]])

# TASK tools: local status analysis only; no Lattice Tasks API calls.
tool("tasks.list", "List synthetic civilian-support workflows", lambda s, a: s["tasks"])
tool("tasks.get", "Get a sample task by --id", lambda s, a: get_or_first(s, "tasks", a.id))
tool("tasks.search", "Search tasks by role, description or ID", lambda s, a: [t for t in s["tasks"] if a.query.casefold() in (t["id"] + t["role"] + t["description"]).casefold()])
tool("tasks.status", "Count workflow status labels", lambda s, a: tally(s["tasks"], "status"))
tool("tasks.count", "Count visible synthetic tasks", lambda s, a: {"preview_tasks": len(s["tasks"]), "full_fleet_task_count": s["snapshot"]["task_count"]})
tool("tasks.validate", "Validate synthetic workflow records", lambda s, a: validate_tasks(s))
tool("tasks.backlog", "List queued synthetic workflows", lambda s, a: [t for t in s["tasks"] if t["status"] == "queued"])
tool("tasks.completion_rate", "Calculate sample completed-task fraction", lambda s, a: {"completed": sum(t["status"] == "completed" for t in s["tasks"]), "sampled": len(s["tasks"]), "fraction": round(sum(t["status"] == "completed" for t in s["tasks"]) / max(len(s["tasks"]), 1), 3)})
tool("tasks.workload", "Count sample workflows by entity", lambda s, a: task_load(s))
tool("tasks.timeline", "Sort sample workflows by synthetic due tick", lambda s, a: sorted([{"id": t["id"], "due_tick": t["due_tick"]} for t in s["tasks"]], key=lambda t: t["due_tick"]))

# OBJECT tools: metadata only; never upload, download or transmit objects.
tool("objects.list", "List synthetic object metadata", lambda s, a: s["objects"])
tool("objects.get", "Get one synthetic object metadata record", lambda s, a: get_or_first(s, "objects", a.id))
tool("objects.search", "Search object IDs by substring", lambda s, a: [o for o in s["objects"] if a.query.casefold() in o["id"].casefold()])
tool("objects.types", "Count object media types", lambda s, a: tally(s["objects"], "kind"))
tool("objects.total_size", "Sum synthetic manifest sizes", lambda s, a: {"bytes": sum(o["size_bytes"] for o in s["objects"]), "objects": len(s["objects"])})
tool("objects.checksums", "Inspect synthetic SHA-256 checksums", lambda s, a: [{"id": o["id"], "sha256": o["sha256"]} for o in s["objects"]])
tool("objects.validate", "Validate object-size and checksum fields", lambda s, a: validate_objects(s))
tool("objects.integrity", "Recompute synthetic object content checksums", lambda s, a: check_integrity(s))
tool("objects.expiring", "Find manifests expiring by a synthetic tick", lambda s, a: [o["id"] for o in s["objects"] if o["expires_tick"] <= s["ticks"] + a.threshold])
tool("objects.manifest", "Generate object inventory and retention summary", lambda s, a: {"count": len(s["objects"]), "earliest_expiry_tick": min((o["expires_tick"] for o in s["objects"]), default=None), "total_bytes": sum(o["size_bytes"] for o in s["objects"])})

# VIDEO tools: stream metadata only, NOT video frames or real cameras.
tool("video.list", "List virtual stream metadata", lambda s, a: s["video"])
tool("video.get", "Get virtual stream metadata by --id", lambda s, a: get_or_first(s, "video", a.id))
tool("video.status", "Count simulated stream lifecycle statuses", lambda s, a: tally(s["video"], "status"))
tool("video.protocols", "Count simulated source protocol labels", lambda s, a: tally(s["video"], "protocol"))
tool("video.resolutions", "List synthetic resolution groups", lambda s, a: dict(sorted(Counter(f"{v['width']}x{v['height']}" for v in s["video"]).items())))
tool("video.bandwidth", "Estimate bitrate of virtual streams", lambda s, a: {"aggregate_kbps": sum(v["bitrate_kbps"] for v in s["video"]), "assumed_not_measured": True})
tool("video.frames", "Estimate frames over synthetic tick window", lambda s, a: {"hypothetical_frames": sum(v["fps"] * s["ticks"] for v in s["video"]), "real_frames": 0})
tool("video.stale", "Show streams with aged synthetic last-frame ticks", lambda s, a: [v["id"] for v in s["video"] if s["ticks"] - v["last_frame_tick"] > a.threshold])
tool("video.validate", "Validate virtual stream metadata", lambda s, a: validate_video(s))
tool("video.manifest", "Summarize virtual stream inventory", lambda s, a: {"count": len(s["video"]), "statuses": tally(s["video"], "status"), "real_camera_connections": 0})

# DEVELOPER tools: readiness checks, documentation and safe configuration.
tool("developer.catalog", "Describe all 50 callable tools", lambda s, a: [{"name": n, "description": d} for n, (d, _) in sorted(TOOLS.items())])
tool("developer.docs", "Return official Lattice developer documentation links", lambda s, a: DOCS)
tool("developer.sdk", "Detect locally installed Python REST SDK", lambda s, a: {"anduril_package_detected": importlib.util.find_spec("anduril") is not None, "install": "python3 -m pip install anduril-lattice-sdk", "connected": False})
tool("developer.auth", "Check credential variable presence without printing secrets", lambda s, a: {name: bool(os.environ.get(name)) for name in ("ENVIRONMENT_TOKEN", "SANDBOXES_TOKEN", "LATTICE_ENDPOINT")})
tool("developer.sandbox", "Summarize approved-sandbox prerequisites", lambda s, a: {"status": "requires developer approval", "docs": DOCS["sandboxes"], "real_api_calls": 0, "operator_action": "complete official enrollment"})
tool("developer.limits", "Display local simulation bounds", lambda s, a: {"max_agents": MAX_AGENTS, "max_ticks": MAX_TICKS, "preview_entities_cap": 10, "physical_devices": 0})
tool("developer.schema", "Document local-vs-official payload compatibility", lambda s, a: {"schema": "gpt-doug.kraken.lattice-preview.v1", "official_lattice_payload": False, "notes": "Read official Entities/Tasks/Objects/Video specs before any authorized integration"})
tool("developer.audit", "Report data provenance and read-only execution controls", lambda s, a: {"origin": "deterministic local simulator", "mode": "offline", "records_sampled": s["sampled"], "network_calls": 0, "side_effects": False})
tool("developer.privacy", "Scan sample records for credential-like strings", lambda s, a: privacy_audit(s))
tool("developer.health", "Combined synthetic data integrity report", lambda s, a: {"entities": validate_entities(s), "tasks": validate_tasks(s), "objects": check_integrity(s), "video": validate_video(s)})

assert len(TOOLS) == 50 and len(set(TOOLS)) == 50, "exactly 50 distinct tools required"


def invoke(name: str, s: dict, args) -> dict:
    if name not in TOOLS:
        raise KeyError(f"unknown tool: {name}")
    return {"tool": name, "mode": "offline-synthetic", "api_compatible": False,
            "sampled_entities": s["sampled"], "result": TOOLS[name][1](s, args)}


HTML = """<!doctype html><html lang='en'><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>GPT-Doug // Lattice 50</title>
<style>body{font:15px system-ui;background:#0b121b;color:#e8eef7;margin:0;padding:24px}
h1{font-size:25px}small,.muted{color:#93a8bf}button{cursor:pointer;background:#182b40;color:#e8eef7;border:1px solid #3b5069;padding:8px;border-radius:7px;text-align:left}
button:hover{background:#23405b}section{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:7px;margin:10px 0 26px}
pre{background:#06101b;padding:16px;border:1px solid #3b5069;white-space:pre-wrap;overflow-wrap:anywhere;max-height:48vh;overflow:auto}
input{background:#172538;color:white;border:1px solid #3b5069;border-radius:5px;padding:6px;width:80px}label{margin-right:16px}
</style><h1>GPT-Doug // Lattice 50 Tools</h1>
<p class='muted'>LOCAL SYNTHETIC PREVIEW ONLY · Not connected to Anduril · No physical robots or live video</p>
<label>Virtual agents <input id='agents' type='number' value='16' min='1' max='1000'></label>
<label>Ticks <input id='ticks' type='number' value='20' min='1' max='1000'></label>
<div id='list'></div><h2>Result</h2><pre id='result' aria-live='polite'>Select a tool above.</pre>
<script>
async function run(name){const a=Number(document.getElementById('agents').value),t=Number(document.getElementById('ticks').value);
 const out=document.getElementById('result');out.textContent='Running '+name+'...';try{
 const r=await fetch('/api/run?tool='+encodeURIComponent(name)+'&agents='+a+'&ticks='+t);
 const x=await r.json();out.textContent=JSON.stringify(x,null,2)}catch(e){out.textContent=String(e)}}
async function start(){const r=await fetch('/api/tools');const items=await r.json();const root=document.getElementById('list');
 for(const prefix of ['entities','tasks','objects','video','developer']){
 const h=document.createElement('h2');h.textContent=prefix.toUpperCase();root.appendChild(h);
 const section=document.createElement('section');for(const item of items.filter(x=>x.name.startsWith(prefix+'.'))){
 const btn=document.createElement('button');btn.textContent=item.name+' — '+item.description;
 btn.addEventListener('click',()=>run(item.name));section.appendChild(btn)}root.appendChild(section)}}start();
</script></html>"""


def serve(port: int) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/":
                    payload, mimetype = HTML.encode(), "text/html; charset=utf-8"
                elif parsed.path == "/api/tools":
                    payload, mimetype = json.dumps([{"name": n, "description": d} for n, (d, _) in sorted(TOOLS.items())]).encode(), "application/json"
                elif parsed.path == "/api/run":
                    q = parse_qs(parsed.query)
                    name = q.get("tool", [""])[0]
                    args = argparse.Namespace(id="", query="", threshold=25)
                    data = dataset(int(q.get("agents", ["16"])[0]), int(q.get("ticks", ["20"])[0]))
                    payload, mimetype = json.dumps(invoke(name, data, args)).encode(), "application/json"
                else:
                    self.send_error(404)
                    return
                status = 200
            except (ValueError, KeyError) as exc:
                status, mimetype, payload = 400, "application/json", json.dumps({"error": str(exc)}).encode()
            self.send_response(status)
            self.send_header("Content-Type", mimetype)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; object-src 'none'")
            self.end_headers()
            self.wfile.write(payload)

    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Local-only Lattice 50 dashboard: http://127.0.0.1:{port}", flush=True)
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("list", help="List 50 tools")
    run = subs.add_parser("run", help="Execute one offline tool")
    run.add_argument("tool", choices=sorted(TOOLS))
    run.add_argument("--agents", type=int, default=16)
    run.add_argument("--ticks", type=int, default=20)
    run.add_argument("--id", default="")
    run.add_argument("--query", default="")
    run.add_argument("--threshold", type=int, default=25)
    server = subs.add_parser("serve", help="Launch read-only browser dashboard bound to loopback")
    server.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.action == "list":
        print(json.dumps([{"name": n, "description": d} for n, (d, _) in sorted(TOOLS.items())], indent=2))
    elif args.action == "serve":
        serve(args.port)
    else:
        try:
            print(json.dumps(invoke(args.tool, dataset(args.agents, args.ticks), args), indent=2))
        except (ValueError, KeyError) as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
