"""VA3LM GeoVision orchestration contract for GPT-DOUG-LLM.

This module does not perform camera capture or biometric recognition. It produces a
bounded implementation plan for authorized, non-identifying object/scene recognition
using EYERIS + Zyra + Palantir Foundry.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

VA3LM_COMMAND = "/VA3LM"
VA3LM_PROFILE = "PALANTIRVABRAIN3LM-GPT-DOUG-LLM-ZYRA-XUNA-SONOXO-ECOSYSTEM"


@dataclass(frozen=True)
class Lane:
    name: str
    responsibility: str
    output: str


LANES = (
    Lane("agent-media", "Ingest explicitly authorized images into Foundry Media Sets.", "media references"),
    Lane("agent-model", "Run generic object/scene inference with a versioned model adapter.", "detections"),
    Lane("agent-geo", "Attach WGS84 camera point and field-of-view geometry.", "geospatial detections"),
    Lane("agent-ontology", "Publish Camera and Detection objects plus review actions.", "Ontology objects"),
    Lane("agent-map", "Render operational map/dashboard views from Ontology data.", "reviewable map evidence"),
    Lane("agent-verify", "Check tests, lineage, permissions, and deployment evidence.", "verification report"),
)

PROHIBITED_IDENTITY_MODES = (
    "face recognition",
    "biometric embeddings",
    "named-person lookup",
    "persistent individual tracking",
)


def build_va3lm_plan(*, camera_source: str = "authorized-media", live: bool = False) -> dict[str, Any]:
    deployment = "LIVE_MODEL_DEPLOYMENT" if live else "BATCH_MODEL_INFERENCE"
    return {
        "command": VA3LM_COMMAND,
        "profile": VA3LM_PROFILE,
        "mode": "NON_IDENTIFYING_OBJECT_SCENE_RECOGNITION",
        "cameraSource": camera_source,
        "deployment": deployment,
        "flow": [
            "MEDIA_SET",
            deployment,
            "WGS84_GEOSPATIAL_ENRICHMENT",
            "CAMERA_DETECTION_ONTOLOGY",
            "MAP_WORKSHOP_OSDK",
            "EVIDENCE",
        ],
        "lanes": [asdict(lane) for lane in LANES],
        "prohibitedIdentityModes": list(PROHIBITED_IDENTITY_MODES),
        "stopWhen": "tests-green-and-target-environment-evidence-recorded",
    }
