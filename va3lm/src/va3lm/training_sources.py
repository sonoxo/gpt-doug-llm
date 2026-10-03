"""Discover registered training sources without fetching or executing their content."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from va3lm.ontology import CANONICAL_OBJECT_TYPES, CANONICAL_RELATIONSHIPS

ROOT = Path(__file__).resolve().parents[3]
SOURCE_ID = "SAFEHOUSE_EVERYDAYSPY_TRAINING_V1"
MANIFEST = "the-black-house/training/safehouse/safehouse.manifest.json"


def load_training_source(root: Path = ROOT) -> dict[str, Any]:
    source = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    kernel = json.loads((root / "the-black-house/kernel/kernel.manifest.json").read_text(encoding="utf-8"))
    if source.get("sourceId") != SOURCE_ID or source.get("schemaVersion") != "1.0.0":
        raise ValueError("TRAINING_SOURCE_SCHEMA_INVALID")
    if source.get("controlPlane") != kernel.get("controlPlane"):
        raise ValueError("TRAINING_SOURCE_CONTROL_PLANE_INVALID")
    if not any(item.get("component") == SOURCE_ID and item.get("contract") == MANIFEST for item in kernel["bindings"]):
        raise ValueError("TRAINING_SOURCE_NOT_BOUND")
    integration = source["integration"]
    if integration.get("mode") != "TRAINING_AND_SIMULATION_ONLY" or integration.get("allowedClassifications") != ["public"]:
        raise ValueError("TRAINING_SOURCE_POLICY_INVALID")
    for names, mapping, canonical in (
        ("objectTypes", "objectTypeMap", CANONICAL_OBJECT_TYPES),
        ("relationships", "relationshipMap", CANONICAL_RELATIONSHIPS),
    ):
        vocabulary = source["ontology"][names]
        mappings = source["ontology"][mapping]
        if set(vocabulary) != set(mappings) or not set(mappings.values()).issubset(canonical):
            raise ValueError("TRAINING_SOURCE_ONTOLOGY_INVALID")
        kernel_types = kernel['objectTypes' if names == 'objectTypes' else 'relationshipTypes']
        if not set(mappings.values()).issubset(kernel_types):
            raise ValueError("TRAINING_SOURCE_KERNEL_VOCABULARY_INVALID")
    pipeline = source.get("rviaPipeline")
    if not isinstance(pipeline, list) or not pipeline or not all(isinstance(step, str) and step for step in pipeline):
        raise ValueError("TRAINING_SOURCE_PIPELINE_INVALID")
    return source


def training_plan() -> dict[str, Any]:
    source = load_training_source()
    return {
        "accepted": True,
        "target": SOURCE_ID,
        "executionState": "LOCAL_PLAN_COMPLETE",
        "sourceId": source["sourceId"],
        "sourceManifest": MANIFEST,
        "ontology": source["ontology"],
        "steps": [{"action": step, "status": "PLANNED"} for step in source["rviaPipeline"]],
        "note": "Registered source and validated training plan. Content ingestion, analysis, and human review have not run.",
    }
