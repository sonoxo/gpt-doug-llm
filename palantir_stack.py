"""Capability map for the GPT-DOUG / Virginia-LLM / Wakeup3lm Palantir integration.

This module distinguishes repository implementation from live enrollment
configuration. Every supported plane has a concrete adapter or governed
capability contract; live verification still depends on credentials,
permissions, licensed products and tenant-side resources owned by the operator.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Optional

from federal_compliance import FederalComplianceProfile
from palantir_defense_osdk import PalantirDefenseOSDK
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
        defense_osdk = PalantirDefenseOSDK(
            self.foundry,
            enabled=_flag("PALANTIR_DEFENSE_OSDK_ENABLED"),
        )

        return [
            PalantirPlane(
                name="Foundry",
                role="governed data integration, transforms, datasets, lineage and application data plane",
                implemented=True,
                configured=foundry_ready,
                adapter="palantir_foundry.FoundryClient",
                integration="Foundry HTTPS REST transport + OAuth/token identity + same-host redirect pinning",
                authority="Foundry enrollment scopes, resource permissions and local policy gates",
                notes="Foundry is the governed data/application substrate; configuration does not imply access to any specific enrollment.",
            ),
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
                name="Defense OSDK",
                role="typed defense-application domain contract for intelligence, mission planning, order of battle and sustainment",
                implemented=True,
                configured=defense_osdk.configured,
                adapter="palantir_defense_osdk.PalantirDefenseOSDK + enrollment-generated OSDK client",
                integration="local capability gate around tenant-generated Defense OSDK types/clients and authorized Foundry/Gotham resources",
                authority="OSDK application scopes, Foundry/Gotham identity, Ontology permissions, markings and local human-review policy",
                notes=(
                    "Intelligence, mission-planning, order-of-battle and sustainment are routable when an authorized OSDK client is provisioned. "
                    "Targeting-and-fires may be represented as read-only ontology/simulation context but is blocked from autonomous local execution."
                ),
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
                "ingest_and_govern": "Foundry",
                "reason": "AIP",
                "operational_state": "Ontology",
                "mission_view": "Gotham",
                "typed_defense_apps": "Defense OSDK",
                "deploy": "Apollo",
                "develop_and_analyze": "JupyterLab",
                "event_automation": "Automate",
            },
            "ecosystem_layers": {
                "data_plane": ["Foundry"],
                "semantic_operational_plane": ["Ontology"],
                "reasoning_plane": ["AIP"],
                "mission_operational_picture": ["Gotham"],
                "application_sdk_plane": ["Defense OSDK"],
                "workflow_plane": ["Automate"],
                "engineering_plane": ["JupyterLab"],
                "delivery_plane": ["Apollo"],
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
                "no autonomous local weapon-targeting or fires execution",
                "no classified processing without an explicitly authorized environment",
                "no claim of Space Force, NSA, NASA, CIA or IC certification without formal agency authorization",
            ],
        }
