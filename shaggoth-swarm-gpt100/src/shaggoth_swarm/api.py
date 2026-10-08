from __future__ import annotations

from dataclasses import asdict

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("Install the API extra with: pip install -e '.[api]'") from exc

from .config import SwarmConfig
from .orchestrator import SwarmOrchestrator


class RunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=20_000)
    fanout: int | None = Field(default=None, ge=1, le=100)


app = FastAPI(title="Shaggoth Swarm GPT-100", version="0.1.0")


@app.get("/health")
def health() -> dict:
    config = SwarmConfig()
    return {"status":"ok","agent_capacity":config.agent_count,"adapter":config.adapter}


@app.post("/v1/swarm/run")
def run_swarm(request: RunRequest) -> dict:
    orchestrator = SwarmOrchestrator()
    return asdict(orchestrator.run(request.goal, fanout=request.fanout))
