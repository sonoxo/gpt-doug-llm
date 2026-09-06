#!/usr/bin/env python3
"""Validate the Black House infrastructure resilience contract.

This checker is intentionally deterministic and defensive. It verifies that the
repository policy preserves human authority, fail-closed handling, rollback,
telemetry, and non-autonomous external execution.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "safety-shield" / "policies" / "infrastructure-resilience.json"


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def main() -> int:
    data = json.loads(POLICY.read_text(encoding="utf-8"))

    require(data.get("mode") == "DEFENSIVE_INFRASTRUCTURE_PROTECTION", "wrong protection mode")
    states = data.get("states") or {}
    require(set(states) == {"GREEN", "AMBER", "RED", "BLACK"}, "state model must be GREEN/AMBER/RED/BLACK")

    controls = {str(x).lower() for x in data.get("required_controls") or []}
    required_fragments = (
        "health telemetry",
        "human override",
        "simulation",
        "rollback",
        "least-privileged",
        "audit evidence",
        "fail-closed",
    )
    for fragment in required_fragments:
        require(any(fragment in item for item in controls), f"missing required control: {fragment}")

    contract = data.get("decision_contract") or {}
    require(contract.get("dispatch_external_action") == "disabled by default", "external dispatch must default to disabled")
    require("human approval" in str(contract.get("mutate", "")).lower(), "material mutation must require human approval")
    require("post-restore validation" in str(contract.get("restore", "")).lower(), "restore must require validation")

    invariants = "\n".join(str(x).lower() for x in data.get("invariants") or [])
    require("model predictions are advisory" in invariants, "model authority boundary missing")
    require("humans retain authority" in invariants, "human authority invariant missing")
    require("no autonomous external dispatch" in invariants, "autonomous external dispatch prohibition missing")
    require("fails closed" in invariants, "fail-closed invariant missing")

    source = data.get("public_reference") or {}
    require(source.get("url") == "https://www.youtube.com/watch?v=jK5k9_Gql-I", "public reference URL drift")
    require("NO_AFFILIATION" in str(source.get("handling", "")), "independence handling missing")

    print("BLACK HOUSE INFRASTRUCTURE RESILIENCE GATE: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"BLACK HOUSE INFRASTRUCTURE RESILIENCE GATE: FAIL // {exc}")
        raise SystemExit(2)
