#!/usr/bin/env python3
"""Validate Kraken Jutsu defensive cyber ontology invariants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_POSTURES = {"analyze_only"}
ALLOWED_EXECUTION = {"none", "authorized_only"}
ALLOWED_TRUST = {"authoritative", "community_verified", "community_reference"}
NETWORK_CAPABLE_KINDS = {"detection_runtime", "detection_corpus", "assessment_corpus"}


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    required = {
        "schema_version",
        "ontology_id",
        "purpose",
        "default_posture",
        "guardrails",
        "object_types",
        "relation_types",
        "sources",
        "mapping_rules",
        "decision_contract",
    }
    missing = sorted(required - set(data))
    if missing:
        errors.append(f"missing required top-level keys: {', '.join(missing)}")
        return errors

    if data["default_posture"] not in ALLOWED_POSTURES:
        errors.append("default_posture must remain analyze_only")

    guardrails = data.get("guardrails", {})
    required_guardrails = {
        "authorized_targets_only": True,
        "network_egress": "deny_by_default",
        "external_mutation": "human_approval_required",
        "credential_collection": "prohibited",
        "destructive_actions": "prohibited",
        "persistence_actions": "prohibited",
        "evidence_required_for_state_change": True,
    }
    for key, expected in required_guardrails.items():
        if guardrails.get(key) != expected:
            errors.append(f"guardrail {key!r} must equal {expected!r}")

    object_types = set(data.get("object_types", []))
    relation_names: set[str] = set()
    for relation in data.get("relation_types", []):
        name = relation.get("name")
        src = relation.get("from")
        dst = relation.get("to")
        if not name or not src or not dst:
            errors.append("every relation_type requires name/from/to")
            continue
        if name in relation_names:
            errors.append(f"duplicate relation type: {name}")
        relation_names.add(name)
        if src not in object_types:
            errors.append(f"relation {name} references unknown source type {src}")
        if dst not in object_types:
            errors.append(f"relation {name} references unknown target type {dst}")

    source_ids: set[str] = set()
    repos: set[str] = set()
    for source in data.get("sources", []):
        sid = source.get("id")
        repo = source.get("repo")
        kind = source.get("kind")
        execution = source.get("execution")
        trust = source.get("trust_tier")

        if not sid or sid in source_ids:
            errors.append(f"invalid or duplicate source id: {sid!r}")
        else:
            source_ids.add(sid)

        if not repo or "/" not in repo or repo in repos:
            errors.append(f"invalid or duplicate source repo: {repo!r}")
        else:
            repos.add(repo)

        if execution not in ALLOWED_EXECUTION:
            errors.append(f"source {sid} has unsupported execution mode {execution!r}")
        if trust not in ALLOWED_TRUST:
            errors.append(f"source {sid} has unsupported trust tier {trust!r}")
        if source.get("provenance_required") is not True:
            errors.append(f"source {sid} must require provenance")

        if kind in NETWORK_CAPABLE_KINDS or execution == "authorized_only":
            if source.get("authorization_required") is not True:
                errors.append(f"network-capable source {sid} must require explicit authorization")
            if execution != "authorized_only":
                errors.append(f"network-capable source {sid} must use authorized_only execution")

    for rule in data.get("mapping_rules", []):
        relation = rule.get("relation")
        if relation not in relation_names:
            errors.append(f"mapping rule {rule.get('id')} references unknown relation {relation!r}")
        if rule.get("input") not in object_types:
            errors.append(f"mapping rule {rule.get('id')} has unknown input type")
        if rule.get("output") not in object_types:
            errors.append(f"mapping rule {rule.get('id')} has unknown output type")

    contract = data.get("decision_contract", {})
    for stage in ("observe", "normalize", "correlate", "rank", "recommend", "execute", "verify"):
        if not contract.get(stage):
            errors.append(f"decision_contract missing stage {stage}")

    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("kraken_jutsu/cyber_ontology.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to read ontology: {exc}")
        return 2

    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {path} passed defensive ontology validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
