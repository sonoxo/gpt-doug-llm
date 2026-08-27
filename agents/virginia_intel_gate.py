#!/usr/bin/env python3
"""Virginia Legal Intelligence Command Gate.

Enforces provenance, legal/evidentiary status, jurisdiction, and command-review
requirements before intelligence records are promoted into downstream ZYRA or
GPT-GLASSONION ontology layers.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POLICY_PATH = Path("intel/policy/legal-facts-framework.json")
REQUIRED_FIELDS = {
    "sourceId",
    "sourceLocation",
    "intelligenceTier",
    "intelligenceClass",
    "provenanceLocator",
    "jurisdiction",
    "statement",
}
HIGH_IMPACT_FIELDS = {"attribution", "identity", "culpability", "legalStatus", "externalDefensiveAction"}


class VirginiaIntelGateError(RuntimeError):
    """Raised when intelligence fails command-gate validation."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VirginiaIntelGateError(f"cannot read intelligence policy {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VirginiaIntelGateError(f"expected JSON object: {path}")
    return value


def load_policy(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    policy = _read_json(root / POLICY_PATH)
    if policy.get("framework") != "ZYRA VIRGINIA LEGAL INTELLIGENCE COMMAND FRAMEWORK":
        raise VirginiaIntelGateError("unexpected intelligence doctrine")
    if policy.get("jurisdiction") != "VIRGINIA":
        raise VirginiaIntelGateError("Virginia command jurisdiction is not active")
    return policy


def _allowed_classes(policy: dict[str, Any]) -> set[str]:
    return set((policy.get("intelligenceClasses") or {}).keys())


def _allowed_tiers(policy: dict[str, Any]) -> set[int]:
    return {int(item["tier"]) for item in policy.get("intelligenceTiers") or [] if "tier" in item}


def validate_intelligence(root: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    policy = load_policy(root)
    missing = sorted(REQUIRED_FIELDS - set(record))
    if missing:
        raise VirginiaIntelGateError(f"intelligence record missing fields: {', '.join(missing)}")

    if record["intelligenceClass"] not in _allowed_classes(policy):
        raise VirginiaIntelGateError(f"unknown intelligence class: {record['intelligenceClass']}")
    if int(record["intelligenceTier"]) not in _allowed_tiers(policy):
        raise VirginiaIntelGateError(f"unknown intelligence tier: {record['intelligenceTier']}")

    jurisdiction = str(record["jurisdiction"]).upper().strip()
    allowed_jurisdictions = {"VIRGINIA", "FEDERAL", "MULTI_JURISDICTION", "NON_VIRGINIA_CONTEXT"}
    if jurisdiction not in allowed_jurisdictions:
        raise VirginiaIntelGateError(f"unsupported jurisdiction tag: {jurisdiction}")

    locator = str(record["provenanceLocator"]).strip()
    if not locator:
        raise VirginiaIntelGateError("provenance locator cannot be empty")
    if not str(record["sourceId"]).strip() or not str(record["sourceLocation"]).strip():
        raise VirginiaIntelGateError("source identity and location are required")
    if not str(record["statement"]).strip():
        raise VirginiaIntelGateError("intelligence statement cannot be empty")

    intelligence_class = str(record["intelligenceClass"])
    if intelligence_class == "LEGAL_RECORD_ALLEGATION" and record.get("adjudicated") is True:
        raise VirginiaIntelGateError("allegation cannot be marked adjudicated")
    if intelligence_class == "ADJUDICATED_LEGAL_FACT" and record.get("adjudicated") is not True:
        raise VirginiaIntelGateError("adjudicated legal fact requires adjudicated=true")
    if intelligence_class in {"MEDIA_INTELLIGENCE_CLAIM", "UNVERIFIED_INTELLIGENCE"}:
        if record.get("factPromotion") is True:
            raise VirginiaIntelGateError("media/unverified intelligence cannot be directly promoted as fact")

    high_impact = bool(HIGH_IMPACT_FIELDS.intersection(record.get("impactFields") or []))
    if high_impact and record.get("commandReview") != "APPROVED":
        raise VirginiaIntelGateError("high-impact intelligence requires commandReview=APPROVED")

    return {
        "gate": "VIRGINIA_LEGAL_INTELLIGENCE_COMMAND",
        "status": "CLEARED",
        "jurisdiction": jurisdiction,
        "intelligenceTier": int(record["intelligenceTier"]),
        "intelligenceClass": intelligence_class,
        "sourceId": record["sourceId"],
        "provenanceLocator": locator,
        "commandReviewRequired": high_impact,
    }


def doctrine_status(root: str | Path) -> str:
    policy = load_policy(root)
    tiers = policy.get("intelligenceTiers") or []
    classes = policy.get("intelligenceClasses") or {}
    return "\n".join(
        [
            "🛰️ VIRGINIA INTELLIGENCE COMMAND // DOCTRINE ACTIVE",
            f"Jurisdiction: {policy['jurisdiction']}",
            f"Intelligence tiers: {len(tiers)}",
            f"Intelligence classes: {len(classes)}",
            "Command rule: provenance + legal status + jurisdiction + corroboration retained",
            "High-impact promotion: COMMAND REVIEW REQUIRED",
            "Automatic guilt/attribution escalation: DISABLED",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Virginia Legal Intelligence Command Gate")
    parser.add_argument("action", choices=["status", "validate"])
    parser.add_argument("record", nargs="?")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        if args.action == "status":
            print(doctrine_status(args.root))
            return 0
        if not args.record:
            raise VirginiaIntelGateError("validate requires a JSON intelligence record path")
        record_path = Path(args.record)
        if not record_path.is_absolute():
            record_path = Path(args.root).resolve() / record_path
        record = _read_json(record_path)
        print(json.dumps(validate_intelligence(args.root, record), indent=2, sort_keys=True))
        return 0
    except VirginiaIntelGateError as exc:
        print(f"VIRGINIA INTELLIGENCE COMMAND // GATE HOLD ❌ // {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
