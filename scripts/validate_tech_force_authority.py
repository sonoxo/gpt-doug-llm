#!/usr/bin/env python3
"""Fail-closed validator for the public TECH FORCE authority policy.

This validator checks repository-local policy integrity only. It does not grant,
verify, or infer any external legal, government, contractual, or operational
authority.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "safety-shield" / "policies" / "tech-force-authority.json"
DISCLAIMER = ROOT / "ECOSYSTEM_DISCLAIMER.md"
OPEN_CALL = ROOT / "TECH_FORCE_OPEN_CALL.md"
CONTRIBUTORS = ROOT / "CONTRIBUTORS_WANTED.md"

EXPECTED_SCHEMA = "black-house.tech-force-authority.v1"
EXPECTED_MODE = "DEFENSIVE_RESEARCH_SIMULATION_ONLY"
EXPECTED_PRINCIPLE = "CAPABILITY_IS_NOT_AUTHORITY"

REQUIRED_BLOCKED_CONCEPTS = (
    "unauthorized third-party access",
    "intrusion or persistence on third-party systems",
    "destructive or disruptive cyber effects",
    "critical-infrastructure control or disruption",
    "weapons targeting or autonomous lethal action",
)

REQUIRED_ALLOWED_CONCEPTS = (
    "defensive cybersecurity",
    "owned or explicitly authorized vulnerability testing",
    "cyber ranges and intentionally vulnerable labs",
    "digital twins and synthetic simulations",
    "resilience and recovery engineering",
)

REQUIRED_TEXT_MARKERS = {
    DISCLAIMER: (
        "Public policy is not operational authorization",
        "disabled unless and until",
    ),
    OPEN_CALL: (
        "civilian/open-source engineering contributor program",
        "not military orders",
    ),
    CONTRIBUTORS: (
        "TECH FORCE",
        "Public contribution work must remain defensive",
    ),
}


def fail(message: str) -> None:
    raise SystemExit(f"TECH FORCE AUTHORITY GATE: FAIL: {message}")


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")


def main() -> None:
    for path in (POLICY, DISCLAIMER, OPEN_CALL, CONTRIBUTORS):
        require_file(path)

    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {POLICY.relative_to(ROOT)}: {exc}")

    if policy.get("schema") != EXPECTED_SCHEMA:
        fail("unexpected or missing policy schema")
    if policy.get("public_repo_mode") != EXPECTED_MODE:
        fail("public_repo_mode must remain DEFENSIVE_RESEARCH_SIMULATION_ONLY")
    if policy.get("principle") != EXPECTED_PRINCIPLE:
        fail("principle must remain CAPABILITY_IS_NOT_AUTHORITY")
    if policy.get("canonical_disclaimer") != DISCLAIMER.name:
        fail("canonical_disclaimer must point to ECOSYSTEM_DISCLAIMER.md")
    if policy.get("open_call") != OPEN_CALL.name:
        fail("open_call must point to TECH_FORCE_OPEN_CALL.md")

    allowed = set(policy.get("allowed_public_modes") or [])
    blocked = set(policy.get("blocked_without_verified_external_authority") or [])

    missing_allowed = [x for x in REQUIRED_ALLOWED_CONCEPTS if x not in allowed]
    if missing_allowed:
        fail(f"required defensive public modes missing: {missing_allowed}")

    missing_blocked = [x for x in REQUIRED_BLOCKED_CONCEPTS if x not in blocked]
    if missing_blocked:
        fail(f"required blocked authority boundaries missing: {missing_blocked}")

    if not blocked:
        fail("blocked_without_verified_external_authority may not be empty")

    for path, markers in REQUIRED_TEXT_MARKERS.items():
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                fail(f"{path.name} missing required marker: {marker!r}")

    print("TECH FORCE AUTHORITY GATE: PASS")
    print(f"schema={policy['schema']}")
    print(f"public_repo_mode={policy['public_repo_mode']}")
    print(f"principle={policy['principle']}")
    print(f"blocked_boundaries={len(blocked)}")
    print("This gate validates repository policy integrity; it does not grant external authority.")


if __name__ == "__main__":
    main()
