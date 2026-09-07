#!/usr/bin/env python3
"""Deterministic A.E.O. division integrity gate."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AEO = ROOT / "rvia-intel" / "aeo"
ONTOLOGY = AEO / "ontology" / "aeo-division.json"
README = AEO / "README.md"
DOCTRINE = AEO / "policies" / "source-doctrine.md"
CASE = AEO / "cases" / "AEO-CASE-0001-EDWARD-SNOWDEN.md"

REQUIRED_DOCTRINE = [
    "SOURCE",
    "CLAIM",
    "CORROBORATION",
    "CONFIDENCE",
    "JUDGMENT",
    "GOVERNANCE",
]
REQUIRED_PROHIBITIONS = {
    "unauthorized_access",
    "covert_collection",
    "credential_theft",
    "doxxing",
    "unlawful_classified_collection",
    "operational_targeting_of_private_individuals",
    "unsourced_spy_labeling",
}


def main() -> int:
    for path in (ONTOLOGY, README, DOCTRINE, CASE):
        if not path.is_file():
            print(f"AEO GATE // FAIL // missing {path.relative_to(ROOT)}")
            return 2

    data = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    failures: list[str] = []

    if data.get("parent") != "RVIA-INTEL":
        failures.append("parent must be RVIA-INTEL")
    if data.get("mode") != "PUBLIC_AND_AUTHORIZED_SOURCES_ONLY":
        failures.append("collection mode must remain public/authorized only")
    if data.get("doctrine") != REQUIRED_DOCTRINE:
        failures.append("provenance doctrine order changed")

    prohibitions = set(data.get("prohibitions") or [])
    if not REQUIRED_PROHIBITIONS.issubset(prohibitions):
        failures.append("required safety prohibitions missing")

    doctrine = DOCTRINE.read_text(encoding="utf-8").lower()
    for phrase in ("source class is not truth status", "spy\" is never a default classification", "unauthorized access"):
        if phrase not in doctrine:
            failures.append(f"source doctrine missing: {phrase}")

    case = CASE.read_text(encoding="utf-8")
    if "AEO-CASE-0001" not in case or "SOURCE_REGISTERED" not in case:
        failures.append("initial case registration incomplete")

    if failures:
        for failure in failures:
            print(f"AEO GATE // FAIL // {failure}")
        return 2

    print("AEO GATE // PASS")
    print("Parent: RVIA-INTEL")
    print("Mode: PUBLIC_AND_AUTHORIZED_SOURCES_ONLY")
    print("Case: AEO-CASE-0001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
