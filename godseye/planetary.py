from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


ROBOTICS_RESEARCH_REFERENCES = [
    {
        "repository": "Roboparty/roboto_origin",
        "category": "humanoid-platform",
        "mode": "PUBLIC_RESEARCH_REFERENCE",
        "actuation": False,
    },
    {
        "repository": "Roboparty/roboparty_deploy",
        "category": "ros2-deployment-reference",
        "mode": "PUBLIC_RESEARCH_REFERENCE",
        "actuation": False,
    },
    {
        "repository": "Roboparty/rsl_rl",
        "category": "reinforcement-learning-reference",
        "mode": "PUBLIC_RESEARCH_REFERENCE",
        "actuation": False,
    },
    {
        "repository": "Roboparty/roboparty_xr_teleop",
        "category": "teleoperation-reference",
        "mode": "PUBLIC_RESEARCH_REFERENCE",
        "actuation": False,
    },
    {
        "repository": "Roboparty/UFO",
        "category": "humanoid-control-research",
        "mode": "PUBLIC_RESEARCH_REFERENCE",
        "actuation": False,
    },
]


def _default_planet_path() -> Path:
    return Path(__file__).resolve().parents[1] / "docs" / "planet" / "index.html"


def _default_source_registry() -> List[Dict[str, Any]]:
    try:
        from agency_cloud.platform import SOURCE_REGISTRY

        return list(SOURCE_REGISTRY)
    except Exception:
        return []


def _extract_forge_url(text: str) -> Optional[str]:
    match = re.search(r"const\s+BASE\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else None


def planetary_status(
    *,
    planet_path: Optional[Path] = None,
    source_registry: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    path = Path(planet_path) if planet_path is not None else _default_planet_path()
    registry = list(source_registry) if source_registry is not None else _default_source_registry()
    errors: List[str] = []
    forge_url: Optional[str] = None

    try:
        text = path.read_text(encoding="utf-8")
        forge_url = _extract_forge_url(text)
        if not forge_url:
            errors.append("XUNIA/MMGIS forge URL not found in planet wrapper")
    except (OSError, UnicodeError) as exc:
        errors.append(f"planet wrapper unavailable: {type(exc).__name__}")

    return {
        "schema": "gpt-doug.planetary-status.v1",
        "status": "ONLINE" if forge_url and not errors else "DEGRADED",
        "partial": bool(errors),
        "errors": errors,
        "planetWrapper": str(path),
        "mmgis": {
            "forgeUrl": forge_url,
            "mode": "READ_ONLY_CONTEXT",
            "realWorldControl": False,
        },
        "sourceCount": len(registry),
        "sources": registry,
        "researchReferences": [dict(item) for item in ROBOTICS_RESEARCH_REFERENCES],
    }


def planetary_layers(status: Dict[str, Any]) -> List[Dict[str, Any]]:
    layers: List[Dict[str, Any]] = []
    for item in status.get("sources", []) or []:
        if not isinstance(item, dict):
            continue
        layers.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "mode": item.get("mode"),
                "freshnessSeconds": item.get("freshnessSeconds"),
                "enabled": True,
            }
        )
    return layers


def _default_warhawk_factory(**kwargs):
    from warhawk import WarHawkSwarm

    return WarHawkSwarm(**kwargs)


def planetary_plan(
    mission: str,
    *,
    warhawk_factory=None,
    status_fn=planetary_status,
) -> Dict[str, Any]:
    cleaned = " ".join((mission or "").split()).strip()
    if not cleaned:
        raise ValueError("mission must not be empty")

    factory = warhawk_factory or _default_warhawk_factory
    planetary = status_fn()
    swarm = factory()
    plan = swarm.plan(cleaned)
    return {
        "schema": "gpt-doug.planetary-plan.v1",
        "mission": cleaned,
        "planetary": planetary,
        "warhawk": plan,
        "authority": "HUMAN_APPROVAL_REQUIRED",
        "realWorldControl": False,
    }
