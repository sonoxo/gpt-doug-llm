from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from va3lm.agent_identity import AgentAccessRequest, AgentIdentity, evaluate_agent_access
from va3lm.agents import roster
from va3lm.auth_manager import AuthProvider, broker_auth
from va3lm.brain import ask
from va3lm.defense_ontology import defense_schema
from va3lm.explainer import explain
from va3lm.ontology import schema
from va3lm.planner import build_plan

app = FastAPI(title="VA3LM", version="0.2.0")


class Prompt(BaseModel):
    text: str


class AgentIdentityInput(BaseModel):
    agent_id: str
    spiffe_id: str
    runtime: str = "VA3LM"
    credential_mode: str = "SHORT_LIVED"
    scopes: list[str] = []
    provenance: list[str] = []
    token_binding: list[str] = ["DPOP", "MTLS"]


class AgentAccessInput(BaseModel):
    identity: AgentIdentityInput
    provider: str
    requested_scopes: list[str] = []
    shared_credential: bool = False
    long_lived_credential: bool = False
    project_wide_grant: bool = False
    organization_wide_grant: bool = False
    human_approved: bool = False


class AuthProviderInput(BaseModel):
    provider_id: str
    kind: str = "OAUTH2"
    allowed_scopes: list[str] = []
    supports_user_delegation: bool = False
    requires_token_binding: bool = True


class BrokerInput(BaseModel):
    request: AgentAccessInput
    provider: AuthProviderInput


def _identity(value: AgentIdentityInput) -> AgentIdentity:
    runtime = value.runtime if value.runtime in {"VA3LM", "ZYRA", "GPT_UAP_XO", "OTHER"} else "OTHER"
    credential_mode = value.credential_mode if value.credential_mode in {"SHORT_LIVED", "USER_DELEGATED"} else "SHORT_LIVED"
    return AgentIdentity(
        agent_id=value.agent_id,
        spiffe_id=value.spiffe_id,
        runtime=runtime,  # type: ignore[arg-type]
        credential_mode=credential_mode,  # type: ignore[arg-type]
        scopes=tuple(value.scopes),
        provenance=tuple(value.provenance),
        token_binding=tuple(value.token_binding),
    )


def _access(value: AgentAccessInput) -> AgentAccessRequest:
    return AgentAccessRequest(
        identity=_identity(value.identity),
        provider=value.provider,
        requested_scopes=tuple(value.requested_scopes),
        shared_credential=value.shared_credential,
        long_lived_credential=value.long_lived_credential,
        project_wide_grant=value.project_wide_grant,
        organization_wide_grant=value.organization_wide_grant,
        human_approved=value.human_approved,
    )


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "va3lm", "port": 8088}


@app.get("/api/status")
def status() -> dict:
    return {
        "name": "VA3LM",
        "brain": "gpt-doug-llm",
        "port": 8088,
        "agents": len(roster()),
        "approvalGate": True,
        "xuniaverseRoot": "sonoxo/xuniadao",
        "defenseLayer": "GCPXUNIA-VIRGINIA-VA3LM",
        "agentIdentity": True,
        "authBroker": True,
    }


@app.get("/api/agents")
def agents() -> list[dict[str, str]]:
    return roster()


@app.get("/api/ontology")
def ontology() -> dict:
    return schema()


@app.get("/api/defense/ontology")
def defense_ontology() -> dict:
    return defense_schema()


@app.post("/api/identity/evaluate")
def identity_evaluate(request: AgentAccessInput) -> dict:
    return asdict(evaluate_agent_access(_access(request)))


@app.post("/api/auth/broker")
def auth_broker(value: BrokerInput) -> dict:
    provider_kind = value.provider.kind if value.provider.kind in {"OAUTH2", "OIDC", "API_KEY_VAULT", "MTLS"} else "OAUTH2"
    provider = AuthProvider(
        provider_id=value.provider.provider_id,
        kind=provider_kind,  # type: ignore[arg-type]
        allowed_scopes=tuple(value.provider.allowed_scopes),
        supports_user_delegation=value.provider.supports_user_delegation,
        requires_token_binding=value.provider.requires_token_binding,
    )
    return asdict(broker_auth(_access(value.request), provider))


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
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>VA3LM 8088</title><style>body{margin:0;background:#07111f;color:#eaf2ff;font-family:ui-monospace,monospace}.wrap{max-width:1100px;margin:auto;padding:32px}.hero{border:1px solid #30527a;border-radius:22px;padding:28px;background:linear-gradient(135deg,#0d1c31,#111827)}h1{font-size:48px;margin:0}.tag{color:#7dd3fc}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:20px}.card{border:1px solid #263b57;border-radius:16px;padding:18px;background:#0b1626}.num{font-size:28px;font-weight:700}button{background:#d4a72c;color:#08111e;border:0;border-radius:10px;padding:12px 16px;font-weight:800;cursor:pointer}input{width:70%;padding:12px;background:#06101c;color:white;border:1px solid #31506f;border-radius:10px}pre{white-space:pre-wrap;background:#050b13;padding:18px;border-radius:14px;min-height:120px}.flow{font-size:18px;line-height:2}</style></head><body><div class='wrap'><div class='hero'><div class='tag'>GCPXUNIA // VIRGINIA AGENTIC LARGE LEARNING LANGUAGE MODEL</div><h1>VA3LM // 8088</h1><p>XUNIAverse defensive coding brain + agent identity + auth broker + ontology + tests + evidence.</p><div class='grid'><div class='card'><div class='num'>9</div>Agents</div><div class='card'><div class='num'>8088</div>Command Port</div><div class='card'><div class='num'>ON</div>Identity Gate</div><div class='card'><div class='num'>ON</div>Auth Broker</div></div></div><div class='grid'><div class='card'><h3>Defense Pipeline</h3><div class='flow'>XUNIA → Identity → GCPXUNIA → VIRGINIA → VA3LM → Guardrail → ZYRA → Evidence</div></div><div class='card'><h3>Run a task</h3><input id='goal' value='Build a FastAPI endpoint with tests'><button onclick='go()'>BUILD PLAN</button></div></div><div class='card'><h3>Output</h3><pre id='out'>Ready.</pre></div></div><script>async function go(){const t=document.getElementById('goal').value;const r=await fetch('/api/plan',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({text:t})});document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2)}</script></body></html>"""
