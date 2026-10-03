#!/usr/bin/env python3
"""Fail-closed validator for the defensive Damn Vulnerable Drone ontology."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path("intel/drone-security/damn-vulnerable-drone-ontology.json")
EXPECTED_MODE = "AUTHORIZED_SIMULATION_DEFENSIVE_ONLY"
EXPECTED_DEPLOYMENT = "LOCAL_BLUEPRINT_NOT_REAL_WORLD_CONTROL"
EXPECTED_GUARDRAILS = {
    "authorizedLabOnly": True,
    "simulationOnly": True,
    "realWorldTargeting": False,
    "autonomousTargeting": False,
    "externalScanning": False,
    "rfInterference": False,
    "deauthenticationExecution": False,
    "credentialAttackExecution": False,
    "exploitExecution": False,
    "commandInjectionExecution": False,
    "firmwareModificationExecution": False,
    "dataExfiltrationExecution": False,
    "arbitraryShell": False,
    "externalMutation": False,
    "humanReviewRequiredForScopeChange": True,
    "sourceClaimsRemainAttributed": True,
}
EXPECTED_SCENARIOS = {
    "reconnaissance",
    "protocol-tampering",
    "denial-of-service",
    "injection",
    "exfiltration",
    "firmware-attacks",
}
EXPECTED_COMPONENTS = {
    "flight-controller",
    "companion-computer",
    "ground-control-station",
    "simulator",
}


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["ontology root must be an object"]

    required = {
        "name", "version", "mode", "deploymentState", "purpose", "sourceSnapshot",
        "interpretationRules", "objectTypes", "linkTypes", "evidence", "objects",
        "links", "actions", "guardrails",
    }
    missing = sorted(required - set(data))
    if missing:
        return [f"missing top-level keys: {', '.join(missing)}"]

    if data.get("mode") != EXPECTED_MODE:
        errors.append(f"mode must remain {EXPECTED_MODE}")
    if data.get("deploymentState") != EXPECTED_DEPLOYMENT:
        errors.append(f"deploymentState must remain {EXPECTED_DEPLOYMENT}")
    if data.get("guardrails") != EXPECTED_GUARDRAILS:
        errors.append("guardrails drift detected")

    snapshot = data.get("sourceSnapshot") or {}
    if snapshot.get("sourceId") != "hackers-arise-dvd-2026-07-29":
        errors.append("unexpected source id")
    if snapshot.get("url") != "https://hackers-arise.com/drone-hacking-hacking-uavs-with-damn-vulnerable-drone/":
        errors.append("source URL drift")

    object_types = {x.get("apiName") for x in data.get("objectTypes", []) if isinstance(x, dict)}
    objects = data.get("objects") or []
    object_ids: set[str] = set()
    scenario_ids: set[str] = set()
    component_ids: set[str] = set()
    for obj in objects:
        if not isinstance(obj, dict):
            errors.append("every object must be an object")
            continue
        oid = obj.get("id")
        otype = obj.get("type")
        props = obj.get("properties")
        if not isinstance(oid, str) or not oid or oid in object_ids:
            errors.append(f"invalid or duplicate object id: {oid!r}")
            continue
        object_ids.add(oid)
        if otype not in object_types:
            errors.append(f"object {oid} references unknown type {otype!r}")
        if not isinstance(props, dict):
            errors.append(f"object {oid} properties must be an object")
        if otype == "ScenarioCategory":
            scenario_ids.add(oid)
        if otype == "Component":
            component_ids.add(oid)

    if scenario_ids != EXPECTED_SCENARIOS:
        errors.append("scenario category set drift detected")
    if component_ids != EXPECTED_COMPONENTS:
        errors.append("component set drift detected")

    link_type_names = {x.get("apiName") for x in data.get("linkTypes", []) if isinstance(x, dict)}
    for link in data.get("links") or []:
        if link.get("type") not in link_type_names:
            errors.append(f"unknown link type: {link.get('type')!r}")
        if link.get("from") not in object_ids:
            errors.append(f"dangling link source: {link.get('from')!r}")
        if link.get("to") not in object_ids:
            errors.append(f"dangling link target: {link.get('to')!r}")

    for action in data.get("actions") or []:
        if action.get("externalMutation") is not False:
            errors.append(f"action {action.get('apiName')} must keep externalMutation=false")
        if action.get("simulationOnly") is not True:
            errors.append(f"action {action.get('apiName')} must remain simulationOnly=true")
        if action.get("requiresAuthorizedScope") is not True:
            errors.append(f"action {action.get('apiName')} must require authorized scope")

    forbidden_terms = (
        "real-world target coordinates",
        "deauth command",
        "exploit payload",
        "firmware patch payload",
        "credential brute force",
    )
    serialized = json.dumps(data).lower()
    for term in forbidden_terms:
        if term in serialized:
            errors.append(f"forbidden operational content present: {term}")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: defensive drone-security ontology is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
