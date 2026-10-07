from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from godseye.fusion import collect_snapshot, snapshot_sources
from godseye.planetary import planetary_layers, planetary_plan, planetary_status
from godseye.query import GoDsEyeQueryEngine


router = APIRouter()
query_engine_factory = GoDsEyeQueryEngine


class GoDsEyeQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class PlanetaryPlanRequest(BaseModel):
    mission: str = Field(min_length=1, max_length=4000)


def _unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail="GoDsEye subsystem unavailable")


def _snapshot_dict() -> Dict[str, Any]:
    try:
        snapshot = collect_snapshot()
        data = snapshot.to_dict() if hasattr(snapshot, "to_dict") else snapshot
        if not isinstance(data, dict):
            raise ValueError("invalid snapshot payload")
        return data
    except (TimeoutError, OSError, RuntimeError, ValueError, TypeError) as exc:
        raise _unavailable(exc) from exc


@router.get("/api/v1/godseye/status")
def api_godseye_status():
    return _snapshot_dict()


@router.get("/api/v1/godseye/sources")
def api_godseye_sources():
    try:
        snapshot = collect_snapshot()
        return {
            "schema": "gpt-doug.godseye-sources.v1",
            "sources": snapshot_sources(snapshot),
        }
    except (TimeoutError, OSError, RuntimeError, ValueError, TypeError) as exc:
        raise _unavailable(exc) from exc


@router.post("/api/v1/godseye/query")
def api_godseye_query(payload: GoDsEyeQueryRequest):
    try:
        result = query_engine_factory().query(payload.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TimeoutError, OSError, RuntimeError, TypeError) as exc:
        raise _unavailable(exc) from exc

    if result.get("status") == "BLOCKED" or (result.get("policy") or {}).get("decision") == "BLOCK":
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Request blocked by GoDsEye policy",
                "policy": result.get("policy") or {},
            },
        )
    return result


@router.get("/api/v1/planetary/status")
def api_planetary_status():
    try:
        return planetary_status()
    except (TimeoutError, OSError, RuntimeError, ValueError, TypeError) as exc:
        raise _unavailable(exc) from exc


@router.get("/api/v1/planetary/layers")
def api_planetary_layers():
    try:
        status = planetary_status()
        return {
            "schema": "gpt-doug.planetary-layers.v1",
            "layers": planetary_layers(status),
        }
    except (TimeoutError, OSError, RuntimeError, ValueError, TypeError) as exc:
        raise _unavailable(exc) from exc


@router.post("/api/v1/planetary/plan")
def api_planetary_plan(payload: PlanetaryPlanRequest):
    try:
        return planetary_plan(payload.mission)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (TimeoutError, OSError, RuntimeError, TypeError) as exc:
        raise _unavailable(exc) from exc
