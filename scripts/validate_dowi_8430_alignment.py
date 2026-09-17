#!/usr/bin/env python3
"""Validate Sonoxo's local DoWI 8430.01 engineering alignment profile.

This validator proves only that repository-local implementation requirements are
present. It does not assert government approval, certification, accreditation,
endorsement, contract status, or authorization.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "safety-shield/policies/dowi-8430-01.json"
RECIPE = ROOT / ".doug/gptdougllmgithubsonoxo.yaml"
DISCLAIMER = ROOT / "ECOSYSTEM_DISCLAIMER.md"
SECURITY_GATE = ROOT / ".github/workflows/security-gate.yml"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    for path in (POLICY, RECIPE, DISCLAIMER, SECURITY_GATE):
        require(path.is_file(), f"missing required artifact: {path.relative_to(ROOT)}")

    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    require(policy.get("policy_id") == "DOWI-8430.01-AMS", "unexpected policy id")

    control_ids = {item.get("id") for item in policy.get("controls", [])}
    require(
        {f"AMS-{number:02d}" for number in range(1, 9)} <= control_ids,
        "AMS-01 through AMS-08 must be defined",
    )

    disclaimer = DISCLAIMER.read_text(encoding="utf-8").lower()
    for phrase in (
        "no false endorsement",
        "capability is not authority",
        "alignment check",
        "implementation mapping",
    ):
        require(phrase in disclaimer, f"disclaimer missing required language: {phrase}")

    recipe = RECIPE.read_text(encoding="utf-8").lower()
    for phrase in (
        "gptdougllmgithubsonoxo",
        "human_approval",
        "cyclonedx_sbom",
        "reuse_decision",
        "fail_closed",
    ):
        require(phrase in recipe, f"recipe missing requirement: {phrase}")

    gate = SECURITY_GATE.read_text(encoding="utf-8").lower()
    for phrase in ("tests", "dependency audit", "cyclonedx"):
        require(phrase in gate, f"security gate missing evidence control: {phrase}")

    print("PASS: DoWI 8430.01 local engineering alignment checks passed")
    print("NOTE: This is not government approval, certification, accreditation, or endorsement.")


if __name__ == "__main__":
    main()
