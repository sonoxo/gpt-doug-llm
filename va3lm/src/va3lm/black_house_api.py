from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from va3lm.ecosystem_telemetry import collect_fleet
from va3lm.green_house import green_house_status
from va3lm.palantir_status import palantir_verification_status
from va3lm.rvia import MissionEnvelope, RVIARouter

router = APIRouter()


@lru_cache(maxsize=1)
def _rvia() -> RVIARouter:
    return RVIARouter()


@router.get("/api/black-house/status")
def black_house_status() -> dict:
    palantir = palantir_verification_status()
    green_house = green_house_status()
    return {
        "controlPlane": "THE_BLACK_HOUSE_V1",
        "kernelVersion": "3.0.0",
        "missionProtocol": "black-house-mission-v1",
        "phases": {
            "1": "COMPLETE",
            "2": "COMPLETE",
            "3": "COMPLETE",
            "4": "COMPLETE",
            "5": "COMPLETE",
            "6": "COMPLETE",
            "7": (
                "LIVE_TENANT_VERIFIED"
                if palantir["liveTenantVerified"]
                else "CODE_COMPLETE_LIVE_TENANT_UNVERIFIED"
            ),
            "8": "COMPLETE",
        },
        "layers": {"greenHouse": green_house},
        "rvia": RVIARouter.manifest(),
        "missionHistory": _rvia().ledger.summary(),
        "palantir": palantir,
        "commandCenter": {"route": "/black-house", "runtime": "VA3LM:8088"},
    }


@router.get("/api/black-house/green-house")
def black_house_green_house() -> dict:
    return green_house_status()


@router.get("/api/black-house/router")
def black_house_router_manifest() -> dict:
    return RVIARouter.manifest()


@router.post("/api/black-house/missions")
def route_black_house_mission(mission: MissionEnvelope) -> dict:
    return _rvia().route(mission)


@router.get("/api/black-house/missions")
def black_house_mission_history(limit: int = 100) -> dict:
    ledger = _rvia().ledger
    return {"summary": ledger.summary(), "missions": ledger.history(limit)}


@router.get("/api/black-house/missions/{mission_id}")
def black_house_mission(mission_id: str) -> dict:
    ledger = _rvia().ledger
    try:
        mission = ledger.get(mission_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"mission": mission, "timeline": ledger.timeline(mission_id)}


@router.get("/api/black-house/telemetry")
def black_house_telemetry(live: bool = True) -> dict:
    return collect_fleet(live=live)


@router.get("/api/black-house/palantir")
def black_house_palantir(execute_aip_model: bool = False) -> dict:
    return palantir_verification_status(execute_aip_model=execute_aip_model)


@router.get("/black-house", response_class=HTMLResponse)
def black_house_command_center() -> str:
    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>THE BLACK HOUSE // COMMAND CENTER</title>
<style>
body{margin:0;background:#05070b;color:#f4f7fb;font-family:ui-monospace,monospace}.wrap{max-width:1280px;margin:auto;padding:28px}.hero{padding:28px;border:1px solid #343a46;border-radius:20px;background:linear-gradient(135deg,#0b0e15,#141821)}h1{font-size:46px;margin:4px 0}.tag{letter-spacing:.14em;color:#b9c3d3}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-top:16px}.card{border:1px solid #2a303b;border-radius:14px;background:#0d1118;padding:16px}.green{border-color:#276749;background:#07150f}.state{font-size:22px;font-weight:800}pre{white-space:pre-wrap;word-break:break-word;background:#070a10;padding:14px;border-radius:10px;max-height:420px;overflow:auto}input,select{background:#070a10;color:#fff;border:1px solid #394252;border-radius:8px;padding:10px;margin:4px;min-width:180px}button{border:0;border-radius:8px;padding:11px 16px;font-weight:800;cursor:pointer}.wide{grid-column:1/-1}small{color:#a9b3c3}a{color:#d7dfec}
</style>
</head>
<body><div class="wrap">
<div class="hero"><div class="tag">GLOBAL GOVERNANCE // RVIA // EVIDENCE // AUDIT</div><h1>THE BLACK HOUSE</h1><p>Mission routing, durable history, live fleet telemetry, governed domain layers, Palantir verification truth state, and the VA3LM command surface.</p></div>
<div class="grid" id="phaseGrid"></div>
<div class="grid">
<div class="card green"><h2>🌿 GREEN HOUSE</h2><small>Eco · Bio · Pharma · FDA</small><pre id="greenHouse">Loading…</pre></div>
<div class="card wide"><h2>MISSION CONSOLE</h2><input id="intent" value="Inspect ecosystem health and return evidence"><select id="target"><option>GPT_DOUG_MAX</option><option>VIRGINIA</option><option>WAKEUP3LM</option><option>ZYRA</option><option>XUNIA</option><option>NXYZ</option><option>ZYRA_CLOUD</option><option>AIP_REGISTRY</option><option>PALANTIR</option></select><label><input type="checkbox" id="mutation"> mutation</label><label><input type="checkbox" id="approved"> approved</label><button onclick="sendMission()">ROUTE MISSION</button><pre id="missionOut">Ready.</pre></div>
<div class="card"><h2>FLEET TELEMETRY</h2><small>GitHub live probe</small><pre id="telemetry">Loading…</pre></div><div class="card"><h2>MISSION HISTORY</h2><pre id="history">Loading…</pre></div><div class="card"><h2>PALANTIR</h2><small>Code state is separate from tenant entitlement.</small><pre id="palantir">Loading…</pre></div><div class="card"><h2>RVIA ROUTER</h2><pre id="router">Loading…</pre></div>
</div></div>
<script>
const pretty=x=>JSON.stringify(x,null,2);
async function load(){const [s,t,h,p,r,g]=await Promise.all([fetch('/api/black-house/status').then(x=>x.json()),fetch('/api/black-house/telemetry?live=true').then(x=>x.json()).catch(e=>({error:String(e)})),fetch('/api/black-house/missions?limit=20').then(x=>x.json()),fetch('/api/black-house/palantir').then(x=>x.json()),fetch('/api/black-house/router').then(x=>x.json()),fetch('/api/black-house/green-house').then(x=>x.json())]);document.getElementById('phaseGrid').innerHTML=Object.entries(s.phases).map(([n,v])=>`<div class="card"><small>PHASE ${n}</small><div class="state">${v}</div></div>`).join('');telemetry.textContent=pretty(t);history.textContent=pretty(h);palantir.textContent=pretty(p);router.textContent=pretty(r);greenHouse.textContent=pretty(g);}
async function sendMission(){const body={requestedBy:'command-center',intent:intent.value,target:target.value,classification:'internal',requiredCapabilities:[],allowedTools:[],approvalState:approved.checked?'APPROVED':'PENDING_POLICY',mutation:mutation.checked};const response=await fetch('/api/black-house/missions',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});missionOut.textContent=pretty(await response.json());await load();}
load();setInterval(load,60000);
</script></body></html>"""


def reset_runtime_for_tests() -> None:
    _rvia.cache_clear()
