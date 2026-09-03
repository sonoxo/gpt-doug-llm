from __future__ import annotations

from copy import deepcopy

PACK_SOURCE = "sonoxo/pack"
PACK_SOURCE_STATE = "ALPHA_REFERENCE"
VA3LM_CAPABILITY_VERSION = "0.6.0"

_CAPABILITIES = [
    {
        "id": "core",
        "sourcePattern": "packages/core",
        "va3lmArea": "shared contracts and runtime primitives",
        "status": "ADAPTED",
    },
    {
        "id": "auth",
        "sourcePattern": "packages/auth",
        "va3lmArea": "operator and Foundry authentication boundaries",
        "status": "ADAPTED_BOUNDARY",
    },
    {
        "id": "schema",
        "sourcePattern": "packages/schema",
        "va3lmArea": "ontology and capability schemas",
        "status": "ADAPTED",
    },
    {
        "id": "document-schema",
        "sourcePattern": "packages/document-schema",
        "va3lmArea": "structured evidence and document contracts",
        "status": "ADAPTED",
    },
    {
        "id": "state",
        "sourcePattern": "packages/state",
        "va3lmArea": "agent workflow and approval-gate state",
        "status": "ADAPTED",
    },
    {
        "id": "codegen",
        "sourcePattern": "packages/codegen",
        "va3lmArea": "typed code-generation contracts",
        "status": "ADAPTED_PATTERN",
    },
    {
        "id": "sdkgen",
        "sourcePattern": "packages/sdkgen",
        "va3lmArea": "generated client and integration boundaries",
        "status": "ADAPTED_PATTERN",
    },
    {
        "id": "app",
        "sourcePattern": "packages/app",
        "va3lmArea": "8088 command-center application surface",
        "status": "ADAPTED",
    },
    {
        "id": "workspace-execution",
        "sourcePattern": "VA3LM native bounded runtime",
        "va3lmArea": "workspace inspection, UTF-8 file edits, rollback backups, allow-listed command execution and evidence capture",
        "status": "ADAPTED",
    },
    {
        "id": "structured-agent-loop",
        "sourcePattern": "VA3LM native validated decision protocol",
        "va3lmArea": "localhost model decision validation, one-shot structural repair, bounded tool rounds, approval holds and non-fabricated completion states",
        "status": "ADAPTED",
    },
    {
        "id": "create-app",
        "sourcePattern": "packages/create-app",
        "va3lmArea": "future VA/RVIA application scaffolding",
        "status": "BLUEPRINT",
    },
    {
        "id": "monorepo",
        "sourcePattern": "packages/monorepo",
        "va3lmArea": "repository consistency, CI and release discipline",
        "status": "ADAPTED",
    },
    {
        "id": "geospatial-tracking",
        "sourcePattern": "Google Maps Platform + NSA public SIGINT workflow reference",
        "va3lmArea": "authorized non-identifying asset/event observations, provenance, confidence, GeoJSON and map review",
        "status": "ADAPTED_BOUNDARY",
    },
    {
        "id": "federal-intel-osint",
        "sourcePattern": "official U.S. government public sources + verified official GitHub organizations",
        "va3lmArea": "CIA/NSA/NRO/NGA-NGP/DIA-GDIP public-source registry, provenance and official-source verification",
        "status": "ADAPTED_BOUNDARY",
    },
]


def capability_manifest() -> dict:
    """Return the Big Virginia capability map derived from safe PACK patterns.

    PACK is treated as an architectural reference. Its own README labels the
    capabilities alpha/not production-ready, so VA3LM does not claim that a
    capability is production-ready merely because a matching PACK package exists.
    """

    return {
        "name": "BIG VIRGINIA // VA3LM Capability Plane",
        "version": VA3LM_CAPABILITY_VERSION,
        "source": PACK_SOURCE,
        "sourceState": PACK_SOURCE_STATE,
        "productionBoundary": "VA3LM-owned tests, security gates, approval gates, deployment validation and observed runtime evidence remain authoritative",
        "capabilities": deepcopy(_CAPABILITIES),
    }


def capability_status() -> dict:
    manifest = capability_manifest()
    capabilities = manifest["capabilities"]
    return {
        "version": manifest["version"],
        "total": len(capabilities),
        "adapted": sum(item["status"].startswith("ADAPTED") for item in capabilities),
        "blueprint": sum(item["status"] == "BLUEPRINT" for item in capabilities),
        "sourceState": manifest["sourceState"],
    }
