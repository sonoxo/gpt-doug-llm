"""Capability map for the GPT-DOUG / Virginia-LLM Palantir integration.

This module does not manufacture Palantir access. It reports the Palantir
planes that the operator has explicitly configured and maps each plane to its
role in the local agent architecture.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Optional

from palantir_foundry import FoundryClient


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class PalantirPlane:
    name: str
    role: str
    configured: bool
    integration: str
    authority: str
    notes: str


class PalantirStack:
    """Provider-aligned capability registry for the Palantir stack."""

    def __init__(self, foundry: Optional[FoundryClient]) -> None:
        self.foundry = foundry

    def planes(self) -> list[PalantirPlane]:
        foundry_ready = self.foundry is not None
        aip_enabled = foundry_ready and _flag("PALANTIR_AIP_ENABLED")
        gotham_enabled = _flag("PALANTIR_GOTHAM_ENABLED")
        apollo_enabled = _flag("PALANTIR_APOLLO_ENABLED")
        jupyter_enabled = foundry_ready and _flag("PALANTIR_JUPYTER_ENABLED")

        return [
            PalantirPlane(
                name="AIP",
                role="agent reasoning, LLM workflows, automations and evals",
                configured=aip_enabled,
                integration="Foundry enrollment + explicit PALANTIR_AIP_ENABLED flag",
                authority="inherits Foundry identity, Ontology permissions and local policy gates",
                notes="AIP is modeled as the governed agent layer; this flag does not grant AIP entitlement.",
            ),
            PalantirPlane(
                name="Ontology",
                role="operational objects, links, properties, actions and governed state",
                configured=foundry_ready,
                integration="existing Foundry Ontology REST bridge",
                authority="Foundry OAuth/token scopes plus object/action permissions",
                notes="Reads are enabled by configured scopes; writes remain locally gated and disabled by default.",
            ),
            PalantirPlane(
                name="Gotham",
                role="defense/intelligence operational view over authorized ontology data",
                configured=gotham_enabled,
                integration="explicit enrollment-side Gotham integration / type mapping",
                authority="Palantir enrollment permissions and markings",
                notes="The repo records Gotham capability only; it does not invent a Gotham credential or bypass enrollment configuration.",
            ),
            PalantirPlane(
                name="Apollo",
                role="continuous delivery, release orchestration and software deployment plane",
                configured=apollo_enabled,
                integration="explicit operator-managed Apollo enrollment/deployment workflow",
                authority="Apollo deployment policy and operator authorization",
                notes="Apollo is treated as deployment control, not as an unrestricted execution channel.",
            ),
            PalantirPlane(
                name="JupyterLab",
                role="Foundry Code Workspace for analysis, model development and Ontology interaction",
                configured=jupyter_enabled,
                integration="Foundry Code Workspaces / JupyterLab",
                authority="workspace lineage, data permissions and Foundry governance",
                notes="Normalized from the requested 'jupiter' label to Palantir-documented JupyterLab Code Workspaces.",
            ),
        ]

    def status(self) -> dict[str, Any]:
        planes = self.planes()
        return {
            "stack": "palantir-enterprise-operating-system",
            "configured_planes": [plane.name for plane in planes if plane.configured],
            "planes": [asdict(plane) for plane in planes],
            "routing": {
                "reason": "AIP",
                "operational_state": "Ontology",
                "mission_view": "Gotham",
                "deploy": "Apollo",
                "develop_and_analyze": "JupyterLab",
            },
            "guardrails": [
                "no ambient authority",
                "no fabricated Palantir entitlement",
                "least privilege",
                "Foundry writes disabled by default",
                "human approval for consequential actions",
                "preserve Palantir markings, provenance and auditability",
            ],
        }
