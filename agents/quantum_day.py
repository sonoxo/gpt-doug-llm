"""Offline, evidence-gated PQC readiness planner for the 24 CFO Act agencies.

No agency access, network probes, remote writes, or compliance certifications.
The OMB M-26-15 profile here applies to non-national-security systems only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "gpt-doug.federal-qday-readiness.v1"
OMB = "https://www.whitehouse.gov/wp-content/uploads/2026/06/M-26-15-Execution-of-the-Migration-to-Post-Quantum-Cryptography.pdf"
NIST = "https://csrc.nist.gov/Projects/post-quantum-cryptography"
GAO = "https://files.gao.gov/reports/GAO-27-108740/index.html"
NSA = "https://www.nsa.gov/Cybersecurity/Post-Quantum-Cybersecurity-Resources/"

# Statutory CFO Act cohort as listed in GAO-27-108740. This is not an
# assertion that an agency's current organization or migration is unchanged.
AGENCIES = (
    ("USDA", "Department of Agriculture"),
    ("DOC", "Department of Commerce"),
    ("DOD", "Department of Defense"),
    ("ED", "Department of Education"),
    ("DOE", "Department of Energy"),
    ("HHS", "Department of Health and Human Services"),
    ("DHS", "Department of Homeland Security"),
    ("HUD", "Department of Housing and Urban Development"),
    ("DOI", "Department of the Interior"),
    ("DOJ", "Department of Justice"),
    ("DOL", "Department of Labor"),
    ("DOS", "Department of State"),
    ("DOT", "Department of Transportation"),
    ("TREAS", "Department of the Treasury"),
    ("VA", "Department of Veterans Affairs"),
    ("EPA", "Environmental Protection Agency"),
    ("GSA", "General Services Administration"),
    ("NASA", "National Aeronautics and Space Administration"),
    ("NSF", "National Science Foundation"),
    ("NRC", "Nuclear Regulatory Commission"),
    ("OPM", "Office of Personnel Management"),
    ("SBA", "Small Business Administration"),
    ("SSA", "Social Security Administration"),
    ("USAID", "U.S. Agency for International Development"),
)

# "required_by" is an agency planning target, not a representation that
# every planning subsection is individually due on the same day.
CONTROLS = {
    "pqc_lead": "Named migration lead and responsibility assignment",
    "governance": "CIO/CISO and component-level migration governance",
    "priority_inventory": "Inventory of HVAs, high impact and long-lived sensitive systems",
    "crypto_inventory": "Quantum-vulnerable cryptography inventory and discovery methodology",
    "risk_prioritization": "Risk-based prioritization and justification",
    "roadmap": "System migration milestones through 2035",
    "tls13_plan": "TLS 1.3 support testing and migration timeline",
    "crypto_agility_plan": "Configuration-driven cryptographic agility plan",
    "vendor_plan": "Cloud, FedRAMP and third-party coordination plan",
    "funding_staffing": "Budget and personnel needs assessment",
    "migration_risk": "Risk management and interim protections",
    "submitted_plan": "Agency PQC migration plan submitted to OMB/ONCD",
    "pilots": "PQC interoperability and deployment testing evidence",
    "legacy_remediation": "Replacement plan for non-migratable assets",
    "tls13_supported": "TLS 1.3 or successor supported in applicable systems",
    "pqc_key_establishment": "PQC key establishment implemented for priority systems",
    "pqc_signatures": "PQC digital signatures implemented for priority systems",
    "full_migration": "Remaining risk-based migration completed",
}

DEADLINES = {
    "plan_submission": "2026-10-22",
    "discovery_phase": "2026-2027",
    "pilot_phase": "2027-2028",
    "tls13_support": "2030-01-02",
    "priority_key_establishment": "2030-12-31",
    "priority_digital_signatures": "2031",
    "remaining_migration": "2035",
}

# Prefixes capture named public-key algorithms and common parameterized forms.
VULNERABLE_PREFIXES = (
    "RSA", "ECDH", "ECDSA", "DH", "DSA", "MQV", "X25519", "X448",
    "ED25519", "ED448", "ECIES",
)
PQC_PREFIXES = ("ML-KEM", "ML-DSA", "SLH-DSA")
TOKEN_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{3,63}$")
EVIDENCE_SOURCES = {"agency_attestation", "official_public_record", "independent_assessment", "test_report"}
PURPOSES = {"key_establishment", "digital_signature", "logical_access"}
ASSET_FIELDS = {
    "token", "algorithms", "purposes", "high_value_asset", "impact",
    "sensitivity", "protect_until_year", "crypto_agile",
}


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _timestamp(value: Any) -> str:
    raw = _nonempty(value, "reviewed_at")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("reviewed_at must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("reviewed_at must include a timezone")
    return parsed.isoformat()


def template() -> dict[str, Any]:
    """Create a complete cohort with no invented assessment evidence."""
    return {
        "schema": SCHEMA,
        "policy_scope": "federal_non_national_security_systems_only",
        "agency_cohort": "GAO-27-108740_CFO_Act_24",
        "sources": {"omb_m26_15": OMB, "nist_pqc": NIST, "gao_27_108740": GAO, "nss_separate": NSA},
        "deadlines": dict(DEADLINES),
        "agencies": {
            key: {"name": name, "controls": {}, "assets": []}
            for key, name in AGENCIES
        },
    }


def validate(payload: Any) -> dict[str, Any]:
    """Accept only explicitly provided sanitized metadata and references."""
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("unsupported readiness schema")
    if payload.get("policy_scope") != "federal_non_national_security_systems_only":
        raise ValueError("policy scope must exclude national security systems")
    if set(payload) - {"schema", "policy_scope", "agency_cohort", "sources", "deadlines", "agencies"}:
        raise ValueError("unsupported top-level metadata")
    baseline = template()
    if payload.get("agency_cohort", baseline["agency_cohort"]) != baseline["agency_cohort"]:
        raise ValueError("agency cohort cannot be redefined by input")
    if payload.get("sources", baseline["sources"]) != baseline["sources"]:
        raise ValueError("official policy-source references cannot be overwritten")
    if payload.get("deadlines", DEADLINES) != DEADLINES:
        raise ValueError("federal milestone dates cannot be overwritten")
    agencies = payload.get("agencies")
    if not isinstance(agencies, dict):
        raise ValueError("agencies must be an object")
    known = dict(AGENCIES)
    if set(agencies) - set(known):
        raise ValueError("unknown agency ID in input")
    for agency, entry in agencies.items():
        if not isinstance(entry, dict) or set(entry) - {"name", "controls", "assets"}:
            raise ValueError(f"{agency}: unsupported agency fields")
        if entry.get("name") != known[agency]:
            raise ValueError(f"{agency}: agency name mismatch")
        controls = entry.get("controls", {})
        assets = entry.get("assets", [])
        if not isinstance(controls, dict) or set(controls) - set(CONTROLS):
            raise ValueError(f"{agency}: invalid control keys")
        if not isinstance(assets, list) or len(assets) > 500:
            raise ValueError(f"{agency}: invalid asset metadata list")
        for control_id, evidence in controls.items():
            if not isinstance(evidence, dict) or set(evidence) != {
                "reference", "reviewer", "reviewed_at", "source_type"
            }:
                raise ValueError(f"{agency}/{control_id}: evidence provenance incomplete")
            _nonempty(evidence["reference"], "reference")
            _nonempty(evidence["reviewer"], "reviewer")
            _timestamp(evidence["reviewed_at"])
            if not isinstance(evidence["source_type"], str) or evidence["source_type"] not in EVIDENCE_SOURCES:
                raise ValueError(f"{agency}/{control_id}: unsupported evidence source type")
        seen: set[str] = set()
        for asset in assets:
            if not isinstance(asset, dict) or set(asset) - ASSET_FIELDS:
                raise ValueError(f"{agency}: unsanitized or unknown asset fields")
            token = _nonempty(asset.get("token"), "token")
            if not TOKEN_RE.fullmatch(token) or token in seen:
                raise ValueError(f"{agency}: invalid or duplicate pseudonymous asset token")
            seen.add(token)
            algorithms = asset.get("algorithms")
            purposes = asset.get("purposes")
            if not isinstance(algorithms, list) or not all(
                isinstance(a, str) and 0 < len(a) <= 64 for a in algorithms
            ) or len(algorithms) > 24:
                raise ValueError(f"{agency}/{token}: invalid algorithm list")
            if not isinstance(purposes, list) or not purposes or not all(
                isinstance(p, str) and p in PURPOSES for p in purposes
            ):
                raise ValueError(f"{agency}/{token}: invalid crypto purposes")
            if type(asset.get("high_value_asset")) is not bool:
                raise ValueError(f"{agency}/{token}: HVA field must be boolean")
            if asset.get("impact") not in {"low", "moderate", "high"}:
                raise ValueError(f"{agency}/{token}: impact must be low/moderate/high")
            if asset.get("sensitivity") not in {"low", "moderate", "high"}:
                raise ValueError(f"{agency}/{token}: invalid sensitivity")
            if asset.get("crypto_agile") is not None and type(asset.get("crypto_agile")) is not bool:
                raise ValueError(f"{agency}/{token}: invalid crypto agility status")
            end_year = asset.get("protect_until_year")
            if end_year is not None and (type(end_year) is not int or not 2026 <= end_year <= 2200):
                raise ValueError(f"{agency}/{token}: invalid data protection year")
    return payload


def assess_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Prioritize from provided metadata; does not test any real system."""
    crypto = [str(a).strip().upper() for a in asset["algorithms"]]
    vulnerable = [a for a in crypto if a.startswith(VULNERABLE_PREFIXES)]
    other = [a for a in crypto if not a.startswith(VULNERABLE_PREFIXES + PQC_PREFIXES)
             and not a.startswith(("AES", "SHA", "HMAC"))]
    high_value = (asset["high_value_asset"] or asset["impact"] == "high"
                  or (asset["sensitivity"] == "high"
                      and (asset.get("protect_until_year") or 0) >= 2030)
                  or "logical_access" in asset["purposes"])
    priority = "P0" if vulnerable and high_value else "P1" if vulnerable or other or not crypto else "P2"
    if asset.get("crypto_agile") is False and priority == "P2":
        priority = "P1"
    targets = []
    if "key_establishment" in asset["purposes"] or "logical_access" in asset["purposes"]:
        targets.append(DEADLINES["priority_key_establishment"])
    if "digital_signature" in asset["purposes"]:
        targets.append(DEADLINES["priority_digital_signatures"])
    return {
        "token": asset["token"],
        "priority": priority,
        "vulnerable_algorithms_reported": vulnerable,
        "unclassified_algorithms": other,
        "targets": targets,
        "crypto_agility_gap": asset.get("crypto_agile") is not True,
        "finding": "migration_review_required" if vulnerable or other else "implementation_validation_required",
    }


def assess(payload: Any) -> dict[str, Any]:
    validate(payload)
    agencies = payload["agencies"]
    result: dict[str, Any] = {}
    for agency_id, name in AGENCIES:
        entry = agencies.get(agency_id, {"name": name, "controls": {}, "assets": []})
        evidence = entry.get("controls", {})
        assets = [assess_asset(asset) for asset in entry.get("assets", [])]
        assets.sort(key=lambda a: (a["priority"], a["token"]))
        result[agency_id] = {
            "name": name,
            "readiness": "NOT_INDEPENDENTLY_VERIFIED",
            "agency_authorization_claimed": False,
            "documented_controls": len(evidence),
            "control_count": len(CONTROLS),
            "evidence_coverage_percent": round(100 * len(evidence) / len(CONTROLS), 1),
            "missing_controls": sorted(set(CONTROLS) - set(evidence)),
            "documented_evidence": {k: evidence[k] for k in sorted(evidence)},
            "assessed_asset_tokens": len(assets),
            "priority_assets": assets,
        }
    return {
        "schema": SCHEMA + ".assessment",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agency_count": len(AGENCIES),
        "verified_ready_agencies": 0,
        "status_note": "Evidence metadata is not an audit or federal authorization; all agencies require independent validation.",
        "source_urls": template()["sources"],
        "deadlines": dict(DEADLINES),
        "agencies": result,
    }


def ontology(payload: Any) -> dict[str, Any]:
    """Generate an ontology graph from the roster and validated evidence."""
    report = assess(payload)
    nodes = [{"id": f"pqc:control:{key}", "kind": "PQCRequirement", "label": value}
             for key, value in CONTROLS.items()]
    edges = []
    for agency_id, info in report["agencies"].items():
        nodes.append({"id": f"agency:{agency_id}", "kind": "CFOActAgency", "label": info["name"],
                      "assessment_state": info["readiness"], "evidence_coverage_percent": info["evidence_coverage_percent"]})
        for control in CONTROLS:
            edges.append({"from": f"agency:{agency_id}", "predicate": "requires_pqc_control",
                          "to": f"pqc:control:{control}",
                          "evidence_state": "recorded_not_independently_verified" if control in payload["agencies"].get(agency_id, {}).get("controls", {}) else "not_provided"})
    return {"schema": SCHEMA + ".ontology", "nodes": nodes, "edges": edges,
            "authority": "planning_evidence_only_not_agency_certification"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GPT-Doug 24-agency Q-Day readiness evidence tool (offline)")
    parser.add_argument("command", choices=("seed", "assess", "ontology", "requirements"))
    parser.add_argument("--input", help="Local sanitized JSON input; defaults to blank 24-agency roster")
    parser.add_argument("--output", help="Write to a new local file; by default prints JSON")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else template()
        if args.command == "seed":
            data = template()
        elif args.command == "assess":
            data = assess(payload)
        elif args.command == "ontology":
            data = ontology(payload)
        else:
            data = {"schema": SCHEMA + ".policy", "controls": CONTROLS,
                    "deadlines": dict(DEADLINES), "sources": template()["sources"]}
        result = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if args.output:
            out = Path(args.output)
            if out.is_symlink() or out.exists():
                raise ValueError("output path exists or is a symbolic link; refusing overwrite")
            out.write_text(result, encoding="utf-8")
        else:
            sys.stdout.write(result)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Q-Day tool error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
