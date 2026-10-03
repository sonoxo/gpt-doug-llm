#!/usr/bin/env python3
"""Deterministic NIST SP 800-53 Rev. 5 profile/compliance gate.

Validates the repository's control-catalog and profile metadata only. This gate
never self-certifies a deployment or substitutes repository evidence for an
external authorization decision.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "intel/compliance/government-intelligence-readiness.json"
PROFILES = ROOT / "intel/compliance/nist-800-53-rev5-profiles.json"
CATALOG = ROOT / "intel/compliance/nist-800-53-rev5-control-catalog.md"
EXPECTED_FAMILIES = {
    "AC", "AT", "AU", "CA", "CM", "CP", "IA", "IR", "MA", "MP",
    "PE", "PL", "PM", "PS", "PT", "RA", "SA", "SC", "SI", "SR",
}
EXPECTED_PROFILES = {"LOW", "MODERATE", "HIGH", "PRIVACY"}
EXPECTED_RELEASE = "5.2.0"


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object: {path}")
    return data


def main() -> int:
    for path in (READINESS, PROFILES, CATALOG):
        if not path.is_file():
            print(f"NIST PROFILE GATE // FAIL // missing {path.relative_to(ROOT)}")
            return 2

    readiness = load_json(READINESS)
    profiles = load_json(PROFILES)
    nist = next(
        (item for item in readiness.get("baselines", []) if item.get("id") == "NIST_SP_800_53_REV5"),
        None,
    )
    if not nist:
        print("NIST PROFILE GATE // FAIL // NIST_SP_800_53_REV5 baseline missing")
        return 2

    failures: list[str] = []
    if nist.get("release") != EXPECTED_RELEASE:
        failures.append(f"readiness release must be {EXPECTED_RELEASE}")
    if profiles.get("release") != EXPECTED_RELEASE:
        failures.append(f"profiles release must be {EXPECTED_RELEASE}")

    families = set(nist.get("families") or [])
    if families != EXPECTED_FAMILIES:
        failures.append("20-family catalog set is incomplete or unexpected")

    profile_ids = {item.get("id") for item in profiles.get("profiles", [])}
    if profile_ids != EXPECTED_PROFILES:
        failures.append("Low/Moderate/High/Privacy profile set is incomplete or unexpected")

    doctrine = str(readiness.get("commandDoctrine", "")).lower()
    if "evidence state" not in doctrine or "self-declare" not in doctrine:
        failures.append("evidence-driven no-self-certification doctrine missing")

    if profiles.get("defaultState") != "UNSELECTED_PENDING_CATEGORIZATION":
        failures.append("profile default must remain unselected pending categorization")

    catalog_text = CATALOG.read_text(encoding="utf-8").lower()
    for required_phrase in (
        "compliance is an evidence state",
        "sp 800-53b",
        "sp 800-53a",
        "not a certification",
    ):
        if required_phrase not in catalog_text:
            failures.append(f"catalog doctrine missing phrase: {required_phrase}")

    if failures:
        for failure in failures:
            print(f"NIST PROFILE GATE // FAIL // {failure}")
        return 2

    print("NIST PROFILE GATE // PASS")
    print(f"Release: {EXPECTED_RELEASE}")
    print("Profiles: LOW, MODERATE, HIGH, PRIVACY")
    print("State: UNSELECTED_PENDING_CATEGORIZATION")
    print("Authorization claim: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
