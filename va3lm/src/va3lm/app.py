from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from va3lm.agents import roster
from va3lm.brain import ask
from va3lm.capabilities import capability_manifest, capability_status
from va3lm.explainer import explain
from va3lm.ontology import schema
from va3lm.planner import build_plan

app = FastAPI(title="VA3LM // BIG VIRGINIA", version="0.2.0")


class Prompt(BaseModel):
    text: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "va3lm", "port": 8088, "version": "0.2.0"}


@app.get("/api/status")
def status() -> dict:
    return {
        "name": "VA3LM // BIG VIRGINIA",
        "brain": "gpt-doug-llm",
        "port": 8088,
        "agents": len(roster()),
        "approvalGate": True,
        "capabilityPlane": capability_status(),
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


@app.post("/api/plan")
def plan(prompt: Prompt) -> dict:
    return build_plan(prompt.text)


@app.post("/api/brain")
def brain(prompt: Prompt) -> dict:
    return ask(prompt.text)


@app.post("/api/explain")
def commercial(prompt: Prompt) -> dict:
    return explain(prompt.text)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    cap = capability_status()
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BIG VIRGINIA // VA3LM 8088</title><style>body{{margin:0;background:#07111f;color:#eaf2ff;font-family:ui-monospace,monospace}}.wrap{{max-width:1100px;margin:auto;padding:32px}}.hero{{border:1px solid #30527a;border-radius:22px;padding:28px;background:linear-gradient(135deg,#0d1c31,#111827)}}h1{{font-size:48px;margin:0}}.tag{{color:#7dd3fc}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:20px}}.card{{border:1px solid #263b57;border-radius:16px;padding:18px;background:#0b1626}}.num{{font-size:28px;font-weight:700}}button{{background:#d4a72c;color:#08111e;border:0;border-radius:10px;padding:12px 16px;font-weight:800;cursor:pointer}}input{{width:70%;padding:12px;background:#06101c;color:white;border:1px solid #31506f;border-radius:10px}}pre{{white-space:pre-wrap;background:#050b13;padding:18px;border-radius:14px;min-height:120px}}.flow{{font-size:18px;line-height:2}}</style></head><body><div class='wrap'><div class='hero'><div class='tag'>VIRGINIA AGENTIC LARGE LEARNING LANGUAGE MODEL</div><h1>BIG VIRGINIA // VA3LM</h1><p>GPT-DOUG-LLM coding brain + PACK-inspired capability plane + ontology + tests + evidence.</p><div class='grid'><div class='card'><div class='num'>{len(roster())}</div>Agents</div><div class='card'><div class='num'>{cap['total']}</div>Capabilities</div><div class='card'><div class='num'>8088</div>Command Port</div><div class='card'><div class='num'>ON</div>Approval Gate</div></div></div><div class='grid'><div class='card'><h3>Capability Plane</h3><div class='flow'>Core → Auth → Schema → State → Codegen → SDK → App → CI / Release</div></div><div class='card'><h3>Run a task</h3><input id='goal' value='Build a FastAPI endpoint with tests'><button onclick='go()'>BUILD PLAN</button></div></div><div class='card'><h3>Output</h3><pre id='out'>Ready. /api/capabilities exposes the Big Virginia capability manifest.</pre></div></div><script>async function go(){{const t=document.getElementById('goal').value;const r=await fetch('/api/plan',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify({{text:t}})}});document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}}</script></body></html>"""
