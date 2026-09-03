"""Capability map for the GPT-DOUG / Virginia-LLM / Wakeup3lm Palantir integration.

This module distinguishes repository implementation from live enrollment
configuration. Every supported plane has a concrete adapter; live verification
still depends on credentials, permissions, licensed products and tenant-side
resources owned by the operator.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Optional

from federal_compliance import FederalComplianceProfile
from palantir_apollo import ApolloClient
from palantir_foundry import FoundryClient
from palantir_gotham import PalantirGothamClient


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class PalantirPlane:
    name: str
    role: str
    implemented: bool
    configured: bool
    adapter: str
    integration: str
    authority: str
    notes: str


class PalantirStack:
    """Provider-aligned capability registry for the Palantir stack."""

    def __init__(self, foundry: Optional[FoundryClient]) -> None:
        self.foundry = foundry

    def planes(self) -> list[PalantirPlane]:
        foundry_ready = self.foundry is not None
        aip_configured = foundry_ready and _flag("PALANTIR_AIP_ENABLED")
        gotham_configured = bool(os.getenv("GOTHAM_BASE_URL", "").strip())
        apollo_configured = bool(os.getenv("APOLLO_URL", "").strip())
        jupyter_configured = foundry_ready and _flag("PALANTIR_JUPYTER_ENABLED")

        return [
            PalantirPlane(
                name="AIP",
                role="agent reasoning, provider-compatible LLM calls, published Logic/function execution, eval regression and Automate effects",
                implemented=True,
                configured=aip_configured,
                adapter="palantir_aip.PalantirAIPClient + wakeup3lm.palantir.Wakeup3LMPalantirBridge",
                integration="AIP model proxy + Ontology Query execution + external eval harness + Automate effect bridge",
                authority="inherits Foundry identity, AIP entitlement, model availability, Ontology permissions and local policy gates",
                notes="Code path is complete; live AIP use still requires AIP enabled on the enrollment and permission to use the selected model/function.",
            ),
            PalantirPlane(
                name="Ontology",
                role="operational objects, links, properties, actions and governed state",
                implemented=True,
                configured=foundry_ready,
                adapter="palantir_foundry.FoundryClient",
                integration="Foundry Ontology REST reads, searches, query execution and human-gated Actions",
                authority="Foundry OAuth/token scopes plus object/action permissions",
                notes="Reads use the authorized token; writes remain locally gated and disabled by default.",
            ),
            PalantirPlane(
                name="Gotham",
                role="defense/intelligence operational data over authorized Gotham objects",
                implemented=True,
                configured=gotham_configured,
                adapter="palantir_gotham.PalantirGothamClient",
                integration="Gotham OAuth/Bearer REST API under /api/gotham/v1",
                authority="Gotham enrollment permissions, markings and token scopes",
                notes="Read and explicitly enabled write paths are implemented; configuration does not manufacture Gotham entitlement.",
            ),
            PalantirPlane(
                name="Apollo",
                role="continuous delivery, release orchestration and software deployment plane",
                implemented=True,
                configured=apollo_configured,
                adapter="palantir_apollo.ApolloClient",
                integration="Apollo Hub GraphQL inspection + documented apollo-cli Product Release publishing",
                authority="Apollo Hub token/service account, product/team permissions and explicit publish approval",
                notes="Publishing is blocked unless the caller explicitly approves and apollo-cli is installed.",
            ),
            PalantirPlane(
                name="JupyterLab",
                role="Foundry Code Workspace for analysis, model development and Ontology interaction",
                implemented=True,
                configured=jupyter_configured,
                adapter="Foundry Code Workspaces integration contract",
                integration="Foundry-managed JupyterLab workspace; Wakeup3lm uses the same Ontology/AIP APIs from external IDE workflows",
                authority="workspace lineage, data permissions and Foundry governance",
                notes="Provisioning JupyterLab itself is tenant-side; repository integration and routing are defined.",
            ),
            PalantirPlane(
                name="Automate",
                role="condition-driven effects using Ontology Actions and AIP Logic",
                implemented=True,
                configured=foundry_ready and _flag("PALANTIR_AUTOMATE_ENABLED"),
                adapter="palantir_automate.PalantirAutomateBridge",
                integration="Action and AIP Logic effect execution contract plus machine-readable manifests",
                authority="Foundry permissions, Automate resource permissions and local human gates for writes",
                notes="Palantir public docs expose Automate primarily as an in-platform application; this adapter does not invent undocumented CRUD endpoints.",
            ),
        ]

    def status(self) -> dict[str, Any]:
        planes = self.planes()
        compliance = FederalComplianceProfile(self.foundry).status()
        return {
            "stack": "palantir-enterprise-operating-system",
            "all_code_planes_implemented": all(plane.implemented for plane in planes),
            "implemented_planes": [plane.name for plane in planes if plane.implemented],
            "configured_planes": [plane.name for plane in planes if plane.configured],
            "planes": [asdict(plane) for plane in planes],
            "routing": {
                "reason": "AIP",
                "operational_state": "Ontology",
                "mission_view": "Gotham",
                "deploy": "Apollo",
                "develop_and_analyze": "JupyterLab",
                "event_automation": "Automate",
            },
            "runtime_verification": {
                "command": "/palantir probe",
                "note": "Live green status requires authorized tenant credentials/resources; repository code cannot create licensing or entitlement.",
            },
            "compliance": compliance,
            "guardrails": [
                "no ambient authority",
                "no fabricated Palantir entitlement",
                "least privilege",
                "Foundry writes disabled by default",
                "human approval for consequential actions",
                "preserve Palantir markings, provenance and auditability",
                "no classified processing without an explicitly authorized environment",
                "no claim of Space Force, NSA, NASA, CIA or IC certification without formal agency authorization",
            ],
        }
