"""Read-only, provenance-labeled projection for the local Shoggoth Nexus HUD.

No credentials, filesystem paths, prompts, or raw mission records leave this API.
The Shaggoth package describes configuration capacity, *not* active agents.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Mapping

ATOMIC_LAYERS: tuple[tuple[str, str, str], ...] = (
    ("L0", "PARTICLE", "Immutable envelope and provenance"),
    ("L1", "ATOM", "One scoped capability invocation"),
    ("L2", "MOLECULE", "Bounded composition of operations"),
    ("L3", "CELL", "Isolated logical agent boundary"),
    ("L4", "SWARM", "Bounded agent coordination"),
    ("L5", "SERVICE", "Authorized services and adapters"),
    ("L6", "FABRIC", "Infrastructure and scaling"),
    ("L7", "GOVERNANCE", "Policy, evidence, and audit"),
)


def _count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return min(value, 1_000_000)


def build_nexus_snapshot(
    defense: Mapping[str, Any],
    *,
    brain: Mapping[str, Any] | None = None,
    swarm: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Allowlist existing defensive, brain and swarm status into a safe UI contract."""

    boundary = defense.get("boundary")
    summary = defense.get("summary")
    if not isinstance(boundary, Mapping) or not isinstance(summary, Mapping):
        raise ValueError("verified local defensive status is required")
    if summary.get("defensive_only") is not True or any(
        boundary.get(key) is not expected
        for key, expected in (
            ("localhost_only", True),
            ("network_actions", False),
            ("external_effects", False),
            ("remote_console", False),
        )
    ):
        raise ValueError("Nexus requires the hardened local-only defensive boundary")

    healthy = _count(summary.get("healthy_controls"))
    total = _count(summary.get("total_controls"))
    verified = healthy is not None and total is not None and total > 0 and healthy == total
    shield = defense.get("shield") or {}
    stats = shield.get("stats", {}) if isinstance(shield, Mapping) else {}
    if not isinstance(stats, Mapping):
        stats = {}
    checks = defense.get("control_checks") or {}
    safe_checks = {
        str(name): bool(value)
        for name, value in checks.items()
        if isinstance(name, str) and isinstance(value, bool) and len(name) < 64
    } if isinstance(checks, Mapping) else {}

    recent = []
    for event in (defense.get("recent") or [])[:16]:
        if not isinstance(event, Mapping):
            continue
        recent.append({
            "timestamp": str(event.get("timestamp", ""))[:40],
            "risk_level": str(event.get("risk_level", "UNKNOWN"))[:24],
            "action": str(event.get("action", "UNKNOWN"))[:24],
            "classification": str(event.get("classification", "UNKNOWN"))[:72],
        })

    brain_data = {
        "state": "UNAVAILABLE", "core_ready": False, "model_ready": False,
        "memory_records": None, "ontology_domains": [], "ontology_available": False,
    }
    if isinstance(brain, Mapping):
        readiness = brain.get("readiness") or {}
        memory = brain.get("memory") or {}
        ontology = brain.get("ontology") or {}
        if isinstance(readiness, Mapping) and isinstance(memory, Mapping) and isinstance(ontology, Mapping):
            core_ready = readiness.get("core_ready") is True
            domains = ontology.get("domains", [])
            brain_data = {
                "state": "CORE_READY" if core_ready else "DEGRADED",
                "core_ready": core_ready,
                "model_ready": readiness.get("model_ready") is True,
                "memory_records": _count(memory.get("records")),
                "ontology_domains": sorted(str(d)[:60] for d in domains if isinstance(d, str))[:40]
                if isinstance(domains, list) else [],
                "ontology_available": ontology.get("available") is True,
            }

    swarm_data = {
        "state": "UNAVAILABLE", "capacity": None,
        "atomic_stack_valid": None, "atomic_layer_count": None,
        "capability_profile": None, "observation": "not_connected",
    }
    if isinstance(swarm, Mapping):
        raw_state = str(swarm.get("status", "")).lower()
        state = raw_state.upper() if raw_state in {"alive", "configured", "degraded"} else "UNKNOWN"
        profile = swarm.get("capability_profile")
        swarm_data = {
            "state": state,
            "capacity": _count(swarm.get("agent_capacity")),
            "atomic_stack_valid": swarm.get("atomic_stack_valid")
            if isinstance(swarm.get("atomic_stack_valid"), bool) else None,
            "atomic_layer_count": _count(swarm.get("atomic_layer_count")),
            "capability_profile": str(profile)[:48] if isinstance(profile, str) else None,
            "observation": "configuration_only" if state == "CONFIGURED" else "reported_heartbeat",
        }

    return {
        "system": "SHOGGOTH-NEXUS",
        "version": "1.0",
        "generated_at": str(defense.get("generated_at", ""))[:48],
        "source": {"defense": "local-verified", "brain": "local-module" if brain is not None else "unavailable",
                   "swarm": "local-module" if swarm is not None else "unavailable"},
        "boundary": {
            "localhost_only": True, "network_actions": False,
            "external_effects": False, "remote_console": False,
            "human_control": True,
        },
        "security": {
            "healthy_controls": healthy, "total_controls": total,
            "verified": bool(verified), "checks": safe_checks,
            "blocked": _count(stats.get("blocked")),
            "quarantined": _count(stats.get("quarantined")),
        },
        "brain": brain_data,
        "swarm": swarm_data,
        "atomic_layers": [
            {"id": layer, "name": name, "description": detail, "kind": "architecture_reference"}
            for layer, name, detail in ATOMIC_LAYERS
        ],
        "recent": recent,
    }


def load_local_brain() -> dict[str, Any] | None:
    """Inspect only the local brain's safe read-only status; never run inference."""
    try:
        from gpt_brain.status import build_status
        return build_status()
    except (ImportError, RuntimeError, OSError, ValueError, TypeError):
        return None


def load_local_swarm() -> dict[str, Any] | None:
    """Read Shaggoth package *configuration*; do not claim agents are running."""
    source = Path(__file__).resolve().parents[1] / "shaggoth-swarm-gpt100" / "src"
    if source.is_dir() and str(source) not in sys.path:
        # The monorepo source is authoritative when the package is not installed.
        sys.path.append(str(source))
    try:
        from shaggoth_swarm.atomic import stack_manifest
        from shaggoth_swarm.config import SwarmConfig
        from shaggoth_swarm.policy import CapabilityPolicy
        from os import getenv
        config = SwarmConfig()
        manifest = stack_manifest()
        return {
            "status": "configured", "agent_capacity": config.agent_count,
            "atomic_stack_valid": manifest.get("valid"),
            "atomic_layer_count": manifest.get("layer_count"),
            "capability_profile": getenv("SHAGGOTH_CAPABILITY_PROFILE", "reasoning"),
            "enabled_capability_count": len(CapabilityPolicy.from_env().allowed),
        }
    except (ImportError, RuntimeError, OSError, ValueError, TypeError):
        return None


def nexus_page() -> str:
    """Load checked-in, dependency-free local UI without remote scripts or fonts."""
    return Path(__file__).with_name("nexus.html").read_text(encoding="utf-8")
