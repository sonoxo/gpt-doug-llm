from __future__ import annotations

from dataclasses import asdict

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("Install the API extra with: pip install -e '.[api]'") from exc

from .config import SwarmConfig
from .connectors import ConnectorConfig
from .orchestrator import SwarmOrchestrator


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20_000)
    fanout: int | None = Field(default=None, ge=1, le=100)


app = FastAPI(title="Shaggoth Swarm GPT-100", version="0.2.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "shaggoth-swarm-gpt100"}


@app.get("/ready")
def ready() -> dict:
    config = SwarmConfig()
    return {
        "status": "ready",
        "agent_capacity": config.agent_count,
        "adapter": config.adapter,
    }


@app.get("/status")
def status() -> dict:
    config = SwarmConfig()
    connectors = ConnectorConfig.from_env()
    return {
        "status": "ok",
        "service": connectors.service_name,
        "service_version": connectors.service_version,
        "agent_capacity": config.agent_count,
        "max_fanout": config.max_fanout,
        "max_depth": config.max_depth,
        "adapter": config.adapter,
        "authorized_endpoint_count": len(connectors.endpoints),
        "connector_interval_seconds": connectors.interval_seconds,
        "connector_max_retries": connectors.max_retries,
        "connector_auth_configured": bool(connectors.bearer_token),
    }


@app.post("/v1/swarm/run")
def run_swarm(request: RunRequest) -> dict:
    orchestrator = SwarmOrchestrator()
    return asdict(orchestrator.run(request.goal, fanout=request.fanout))
