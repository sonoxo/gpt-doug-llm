from __future__ import annotations

import os
from dataclasses import asdict

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("Install the API extra with: pip install -e '.[api]'") from exc

from .atomic import stack_manifest
from .capabilities import CAPABILITY_CATALOG
from .config import SwarmConfig
from .connectors import ConnectorConfig
from .orchestrator import SwarmOrchestrator
from .policy import CapabilityPolicy
from .visual import build_visual_data, render_visual_dashboard


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20_000)
    fanout: int | None = Field(default=None, ge=1, le=100)


app = FastAPI(title="Shaggoth Swarm GPT-100", version="0.3.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "shaggoth-swarm-gpt100"}


@app.get("/ready")
def ready() -> dict:
    config = SwarmConfig()
    return {"status": "ready", "agent_capacity": config.agent_count, "adapter": config.adapter}


@app.get("/status")
def status() -> dict:
    config = SwarmConfig()
    connectors = ConnectorConfig.from_env()
    policy = CapabilityPolicy.from_env()
    manifest = stack_manifest()
    return {
        "status": "ok",
        "service": connectors.service_name,
        "service_version": connectors.service_version,
        "agent_capacity": config.agent_count,
        "max_fanout": config.max_fanout,
        "max_depth": config.max_depth,
        "adapter": config.adapter,
        "capability_profile": os.getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning"),
        "enabled_capability_count": len(policy.allowed),
        "supported_capability_count": len(CAPABILITY_CATALOG),
        "authorized_endpoint_count": len(connectors.endpoints),
        "connector_interval_seconds": connectors.interval_seconds,
        "connector_max_retries": connectors.max_retries,
        "connector_auth_configured": bool(connectors.bearer_token),
        "atomic_stack_valid": manifest["valid"],
        "atomic_layer_count": manifest["layer_count"],
    }


@app.get("/visual", response_class=HTMLResponse)
def visual() -> HTMLResponse:
    return HTMLResponse(render_visual_dashboard(), headers={"Cache-Control": "no-store"})


@app.get("/visual/data")
def visual_data() -> dict:
    return build_visual_data()


@app.get("/layers")
def layers() -> dict:
    return stack_manifest()


@app.get("/capabilities")
def capabilities() -> dict:
    policy = CapabilityPolicy.from_env()
    return {
        "profile": os.getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning"),
        "enabled": sorted(policy.allowed),
        "supported": [
            {
                "name": spec.name,
                "description": spec.description,
                "risk": spec.risk.value,
                "requires_scope": spec.requires_scope,
            }
            for spec in CAPABILITY_CATALOG
        ],
    }


@app.post("/v1/swarm/run")
def run_swarm(request: RunRequest) -> dict:
    orchestrator = SwarmOrchestrator()
    return asdict(orchestrator.run(request.goal, fanout=request.fanout))
