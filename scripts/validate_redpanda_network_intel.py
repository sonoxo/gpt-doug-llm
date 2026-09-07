#!/usr/bin/env python3
"""Validate GPT-REDPANDA network-intelligence source/brief/ontology wiring."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/youtube-OqmJb826mY4.json"
BRIEF = ROOT / "intel/briefings/2026-09-07-redpanda-networking-ethical-hackers.md"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/redpanda-network-intel-v1.json"
REDPANDA_README = ROOT / "gpt-redpanda-llm/README.md"
INTEL_README = ROOT / "intel/README.md"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    source = load_json(SOURCE)
    ontology = load_json(ONTOLOGY)

    assert source["id"] == "youtube-OqmJb826mY4"
    assert source["target_agent"] == "GPT-REDPANDA-LLM"
    assert source["controls"]["real_world_targeting"] is False
    assert source["controls"]["defensive_analysis"] is True

    assert ontology["ontology"] == "GPT_REDPANDA_NETWORK_INTEL_V1"
    assert ontology["source_id"] == source["id"]

    blocked = set(ontology["governed_actions"]["BLOCK"])
    required_blocked = {
        "third_party_targeting",
        "credential_interception_or_theft",
        "unauthorized_mitm",
        "service_disruption",
    }
    assert required_blocked.issubset(blocked)

    for path in (BRIEF, REDPANDA_README, INTEL_README):
        if not path.exists():
            raise AssertionError(f"missing required file: {path.relative_to(ROOT)}")

    brief_text = BRIEF.read_text(encoding="utf-8")
    redpanda_text = REDPANDA_README.read_text(encoding="utf-8")
    intel_text = INTEL_README.read_text(encoding="utf-8")

    assert "OqmJb826mY4" in brief_text
    assert "redpanda-network-intel-v1.json" in redpanda_text
    assert "2026-09-07-redpanda-networking-ethical-hackers.md" in intel_text

    print("GPT-REDPANDA network intel validation: GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
