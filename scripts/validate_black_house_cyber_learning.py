#!/usr/bin/env python3
"""Validate the Black House ethical-hacking learning layer using stdlib only."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/youtube-ug8W0sFiVJo.json"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/black-house-ethical-hacking-course-ontology.json"
REQUIRED_DOCS = [
    ROOT / "training/black-house-cyber/README.md",
    ROOT / "training/black-house-cyber/AUTHORIZED_LAB_POLICY.md",
    ROOT / "training/black-house-cyber/CURRICULUM.md",
    ROOT / "training/black-house-cyber/WIFI_DEFENSE.md",
    ROOT / "training/black-house-cyber/PACKET_ANALYSIS.md",
    ROOT / "training/black-house-cyber/EVALS.md",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    errors: list[str] = []

    for path in [SOURCE, ONTOLOGY, *REQUIRED_DOCS]:
        if not path.exists():
            errors.append(f"missing required learning artifact: {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    source = load_json(SOURCE)
    ontology = load_json(ONTOLOGY)

    if source.get("learning_mode") != "AUTHORIZED_LAB_ONLY":
        errors.append("source learning_mode must be AUTHORIZED_LAB_ONLY")

    controls = source.get("controls", {})
    for key in ("real_world_targeting", "credential_theft", "uncontrolled_deauthentication", "third_party_wifi_testing"):
        if controls.get(key) is not False:
            errors.append(f"source control {key} must be false")

    action_classes = ontology.get("action_classes", {})
    for state in ("ALLOW", "REVIEW", "BLOCK"):
        if not action_classes.get(state):
            errors.append(f"ontology action class {state} must be populated")

    required_blocks = {
        "third_party_targeting",
        "uncontrolled_wireless_deauthentication",
        "credential_theft",
    }
    actual_blocks = set(action_classes.get("BLOCK", []))
    missing_blocks = sorted(required_blocks - actual_blocks)
    if missing_blocks:
        errors.append("missing required BLOCK controls: " + ", ".join(missing_blocks))

    if ontology.get("source_id") != source.get("id"):
        errors.append("ontology source_id does not match source record")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("BLACK HOUSE CYBER LEARNING VALIDATION: PASS")
    print(f"modules={len(ontology.get('entities', {}).get('learning_module', []))}")
    print(f"allow={len(action_classes['ALLOW'])} review={len(action_classes['REVIEW'])} block={len(action_classes['BLOCK'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
