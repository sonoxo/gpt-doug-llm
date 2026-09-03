from __future__ import annotations

import json
import os
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from va3lm.agent_runtime import run_coding_agent
from va3lm.agents import roster
from va3lm.black_house_api import router as black_house_router
from va3lm.brain import ask
from va3lm.capabilities import capability_manifest, capability_status
from va3lm.explainer import explain
from va3lm.federal_intel import (
    federal_intel_entity,
    federal_intel_manifest,
    verified_github_sources,
)
from va3lm.max_memory import memory_manager
from va3lm.ontology import schema
from va3lm.planner import build_plan
from va3lm.tracking import TrackingObservation, sample_track, to_geojson, tracking_manifest
from va3lm.workspace import WorkspaceError, WorkspaceRuntime

app = FastAPI(title="VA3LM // BIG VIRGINIA // GPT-DOUG-MAX", version="0.6.0")
app.include_router(black_house_router)


class Prompt(BaseModel):
    text: str
    session_id: str = "default"


class AgentRequest(BaseModel):
    text: str
    approved: bool = False
    max_rounds: int = Field(default=4, ge=1, le=8)


class TrackingBatch(BaseModel):
    observations: list[TrackingObservation]


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "va3lm", "port": 8088, "version": "0.6.0"}


@app.get("/api/status")
def status() -> dict:
    federal_intel = federal_intel_manifest()
    workspace = WorkspaceRuntime().status()
    return {
        "name": "VA3LM // BIG VIRGINIA // MAX",
        "architecture": "agentic-runtime-control-plane",
        "brain": os.getenv("VA3LM_MODEL_NAME", "gpt-doug-llm-max"),
        "port": 8088,
        "agents": len(roster()),
        "approvalGate": True,
        "memory": memory_manager.status(),
        "capabilityPlane": capability_status(),
        "workspace": workspace,
        "httpMutationsEnabled": _truthy("VA3LM_HTTP_MUTATIONS_ENABLED"),
        "tracking": {"mode": "AUTHORIZED_NON_IDENTIFYING", "mapProvider": "Google Maps Platform"},
        "federalIntel": {
            "mode": federal_intel["mode"],
            "entities": len(federal_intel["entities"]),
            "verifiedGitHubEntities": len(verified_github_sources()),
        },
        "claims": {
            "foundationModelTrainedHere": False,
            "liveFoundryOntology": False,
            "deploymentPlane": False,
        },
    }


@app.get("/api/agents")
def agents() -> list[dict[str, str]]:
    return roster()


@app.get("/api/ontology")
def ontology() -> dict:
    return schema()


@app.get("/api/capabilities")
def capabilities() -> dict:
    return capability_manifest()


@app.get("/api/workspace")
def workspace_status() -> dict:
    try:
        runtime = WorkspaceRuntime()
        return {"runtime": runtime.status(), "project": runtime.inspect_project()}
    except WorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/memory/{session_id}")
def memory_snapshot(session_id: str, query: str = "") -> dict:
    return memory_manager.get(session_id).snapshot(query)


@app.delete("/api/memory/{session_id}")
def memory_clear(session_id: str) -> dict:
    return {"sessionId": session_id, "cleared": memory_manager.clear(session_id)}


@app.get("/api/federal-intel")
def federal_intel() -> dict:
    return federal_intel_manifest()


@app.get("/api/federal-intel/github")
def federal_intel_github() -> dict:
    return {
        "mode": "VERIFIED_OFFICIAL_GITHUB_ONLY",
        "sources": verified_github_sources(),
    }


@app.get("/api/federal-intel/{entity_id}")
def federal_intel_by_id(entity_id: str) -> dict:
    try:
        return federal_intel_entity(entity_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/tracking")
def tracking() -> dict:
    return tracking_manifest()


@app.get("/api/tracking/sample")
def tracking_sample() -> dict:
    return to_geojson(sample_track())


@app.post("/api/tracking/geojson")
def tracking_geojson(batch: TrackingBatch) -> dict:
    return to_geojson(batch.observations)


@app.post("/api/plan")
def plan(prompt: Prompt) -> dict:
    return build_plan(prompt.text)


@app.post("/api/brain")
def brain(prompt: Prompt) -> dict:
    return ask(prompt.text, prompt.session_id)


@app.post("/api/agent/execute")
def agent_execute(request: AgentRequest) -> dict:
    approved = request.approved and _truthy("VA3LM_HTTP_MUTATIONS_ENABLED")
    result = run_coding_agent(
        request.text,
        approved=approved,
        max_rounds=request.max_rounds,
    )
    if request.approved and not approved:
        result["httpApprovalHold"] = (
            "Request asked for mutations, but VA3LM_HTTP_MUTATIONS_ENABLED is not true. "
            "No HTTP mutation approval was granted."
        )
    return result


@app.post("/api/explain")
def commercial(prompt: Prompt) -> dict:
    return explain(prompt.text)


@app.get("/tracking-map", response_class=HTMLResponse)
def tracking_map() -> str:
    api_key = os.getenv("GOOGLE_MAPS_BROWSER_KEY", "").strip()
    if not api_key:
        return """<!doctype html><html><body style='background:#07111f;color:#eaf2ff;font-family:monospace;padding:32px'><h1>BIG VIRGINIA // TRACKING MAP</h1><p>Google Maps is not configured.</p><pre>export GOOGLE_MAPS_BROWSER_KEY='YOUR_BROWSER_RESTRICTED_KEY'\nva3lm serve</pre><p>Enable the Maps JavaScript API in your Google Cloud project and restrict this browser key by HTTP referrer. Never commit it to Git.</p></body></html>"""

    geojson = to_geojson(sample_track())
    points = [
        {
            "lat": feature["geometry"]["coordinates"][1],
            "lng": feature["geometry"]["coordinates"][0],
            "label": feature["properties"]["label"],
            "observedAt": feature["properties"]["observedAt"],
            "sequence": feature["properties"]["sequence"],
        }
        for feature in geojson["features"]
    ]
    serialized = json.dumps(points).replace("<", "\\u003c")
    encoded_key = quote(api_key, safe="")
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BIG VIRGINIA // Google Maps Tracking</title><style>html,body,#map{{height:100%;margin:0}}#panel{{position:absolute;z-index:2;top:16px;left:16px;max-width:420px;background:#07111fee;color:#fff;padding:16px;border:1px solid #30527a;border-radius:14px;font:14px ui-monospace,monospace}}#panel b{{font-size:18px}}</style></head><body><div id='panel'><b>BIG VIRGINIA // VA3LM TRACKING</b><br>Authorized non-identifying demo asset.<br>Observed track = recorded points, not inferred surveillance.</div><div id='map'></div><script>const points={serialized};function initMap(){{const start=points[0];const map=new google.maps.Map(document.getElementById('map'),{{center:start,zoom:15,mapTypeControl:true,streetViewControl:false}});const bounds=new google.maps.LatLngBounds();const path=[];for(const point of points){{const pos={{lat:point.lat,lng:point.lng}};path.push(pos);bounds.extend(pos);new google.maps.Marker({{position:pos,map,title:`${{point.sequence}}. ${{point.label}} — ${{point.observedAt}}`,label:String(point.sequence)}});}}new google.maps.Polyline({{path,map,geodesic:true,strokeOpacity:0.9,strokeWeight:4}});map.fitBounds(bounds);}}</script><script async src='https://maps.googleapis.com/maps/api/js?key={encoded_key}&callback=initMap&v=weekly'></script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    cap = capability_status()
    federal_intel = federal_intel_manifest()
    memory = memory_manager.status()
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BIG VIRGINIA // GPT-DOUG-MAX // VA3LM 8088</title><style>body{{margin:0;background:#07111f;color:#eaf2ff;font-family:ui-monospace,monospace}}.wrap{{max-width:1100px;margin:auto;padding:32px}}.hero{{border:1px solid #30527a;border-radius:22px;padding:28px;background:linear-gradient(135deg,#0d1c31,#111827)}}h1{{font-size:48px;margin:0}}.tag{{color:#7dd3fc}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:20px}}.card{{border:1px solid #263b57;border-radius:16px;padding:18px;background:#0b1626}}.num{{font-size:28px;font-weight:700}}button{{background:#d4a72c;color:#08111e;border:0;border-radius:10px;padding:12px 16px;font-weight:800;cursor:pointer}}input{{width:70%;padding:12px;background:#06101c;color:white;border:1px solid #31506f;border-radius:10px}}pre{{white-space:pre-wrap;background:#050b13;padding:18px;border-radius:14px;min-height:120px}}.flow{{font-size:18px;line-height:2}}a{{color:#7dd3fc}}</style></head><body><div class='wrap'><div class='hero'><div class='tag'>VIRGINIA AGENTIC CODING RUNTIME // MAX MEMORY</div><h1>GPT-DOUG-LLM-MAX</h1><p>VA3LM is a bounded agentic runtime/control plane around a configured local model. It can inspect a workspace and, with explicit approval, edit files and run allow-listed development commands. It does not claim a separately trained foundation model or a deployment result without evidence.</p><div class='grid'><div class='card'><div class='num'>{len(roster())}</div>Agents</div><div class='card'><div class='num'>{cap['total']}</div>Capabilities</div><div class='card'><div class='num'>{memory['sessions']}</div>Active Memory Sessions</div><div class='card'><div class='num'>{len(federal_intel['entities'])}</div>Federal Intel Entities</div><div class='card'><div class='num'>MAP</div><a href='/tracking-map'>Google Maps tracking</a></div><div class='card'><div class='num'>BH</div><a href='/black-house'>Black House Command Center</a></div></div></div><div class='grid'><div class='card'><h3>MAX Runtime</h3><div class='flow'>Prompt → Structured Decision → Workspace Tool → Evidence → Repair → Validation → Stop</div></div><div class='card'><h3>Ask the brain</h3><input id='goal' value='Build a FastAPI endpoint with tests'><button onclick='go()'>ASK MAX</button></div></div><div class='card'><h3>Output</h3><pre id='out'>Ready. The dashboard brain endpoint provides guidance; use /api/agent/execute for the bounded coding executor. HTTP mutations remain disabled unless VA3LM_HTTP_MUTATIONS_ENABLED=true and the request explicitly approves them.</pre></div></div><script>async function go(){{const t=document.getElementById('goal').value;const r=await fetch('/api/brain',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{text:t,session_id:'dashboard'}})}});document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}}</script></body></html>"""
