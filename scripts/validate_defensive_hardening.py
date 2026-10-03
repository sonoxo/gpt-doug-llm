#!/usr/bin/env python3
"""Validate GPT-DOUG / XUNIA defensive hardening invariants."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "safety-shield" / "policies" / "defensive-hardening.json"


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def main() -> int:
    data = json.loads(POLICY.read_text(encoding="utf-8"))

    require(data.get("mode") == "DEFENSIVE_HIGH_ASSURANCE", "wrong hardening mode")

    principles = {str(x).lower() for x in data.get("principles") or []}
    for fragment in (
        "country-neutral",
        "least privilege",
        "fail closed",
        "human approval",
        "reproducible builds",
    ):
        require(any(fragment in item for item in principles), f"missing principle: {fragment}")

    controls = {str(x).lower() for x in data.get("required_controls") or []}
    for fragment in (
        "dependency",
        "provenance",
        "secret",
        "permission",
        "sandbox",
        "rollback",
        "tamper-evident",
        "post-change",
    ):
        require(any(fragment in item for item in controls), f"missing control: {fragment}")

    prohibited = {str(x).lower() for x in data.get("prohibited") or []}
    for fragment in (
        "malware",
        "credential theft",
        "unauthorized persistence",
        "destructive exploitation",
        "offensive intrusion",
        "weapon control",
        "automatic target generation",
        "country-specific attack logic",
        "bypassing authorization",
    ):
        require(any(fragment in item for item in prohibited), f"missing prohibition: {fragment}")

    contract = data.get("autonomy_contract") or {}
    require(contract.get("dispatch_external_action") == "disabled by default", "external dispatch must default off")
    require(contract.get("offensive_action") == "prohibited", "offensive action must be prohibited")
    require("human approval" in str(contract.get("mutate_material", "")).lower(), "material mutation must require human approval")

    states = set((data.get("review_states") or {}).keys())
    require(states == {"GREEN", "AMBER", "RED", "BLACK"}, "review states must be GREEN/AMBER/RED/BLACK")

    print("GPT-DOUG DEFENSIVE HARDENING GATE: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"GPT-DOUG DEFENSIVE HARDENING GATE: FAIL // {exc}")
        raise SystemExit(2)
