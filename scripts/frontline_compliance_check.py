#!/usr/bin/env python3
"""Deterministic preflight checker for frontline tool build manifests.

This checker intentionally does not make legal determinations. It enforces the
repository's engineering gates so unresolved compliance questions cannot be
silently converted into approval by an LLM/agent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def get(obj, path, default=None):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def evaluate(m: dict) -> dict:
    reasons: list[str] = []
    state = "GREEN"

    def black(reason: str):
        nonlocal state
        state = "BLACK"
        reasons.append(reason)

    def red(reason: str):
        nonlocal state
        if state != "BLACK":
            state = "RED"
        reasons.append(reason)

    def amber(reason: str):
        nonlocal state
        if state == "GREEN":
            state = "AMBER"
        reasons.append(reason)

    if get(m, "incident.controlled_data_spill") is True:
        black("Controlled/classified data spill flagged; quarantine and incident response required.")

    if get(m, "mission.autonomous_weapon_release") is True:
        red("Autonomous weapon-release functionality is outside this repository's authorized build lane.")
    if get(m, "mission.autonomous_target_selection") is True:
        red("Autonomous target-selection functionality is outside this repository's authorized build lane.")
    if get(m, "mission.unrestricted_offensive_cyber") is True:
        red("Unrestricted offensive cyber functionality is outside this repository's authorized build lane.")

    classification = get(m, "data.classification", "UNKNOWN")
    if classification == "UNKNOWN":
        amber("Data classification is unresolved.")

    if classification == "CLASSIFIED" and get(m, "environment.classified_accredited") is not True:
        red("Classified data requires an explicitly authorized/accredited classified environment.")
    if classification == "CLASSIFIED" and get(m, "security.program_authorization_verified") is not True:
        amber("Classified program authorization/access evidence is missing.")

    jurisdiction = get(m, "export.jurisdiction_status", "UNRESOLVED")
    if jurisdiction == "UNRESOLVED":
        amber("Export jurisdiction is unresolved; obtain program/export-control determination before controlled work proceeds.")

    if classification == "EXPORT_CONTROLLED" and get(m, "export.recipient_authorized") is not True:
        red("Recipient authorization for export-controlled information is not verified.")

    external = get(m, "model.external_egress") is True
    if external and classification in {"CUI", "CUI_CTI"} and get(m, "model.authorized_for_data_class") is not True:
        red("External model egress is not authorized for this CUI data class.")
    if external and classification == "EXPORT_CONTROLLED" and get(m, "model.authorized_for_export_controlled") is not True:
        red("External model egress is not authorized for export-controlled data.")
    if get(m, "data.contains_secret_credentials") is True and get(m, "model.prompt_includes_secret_credentials") is True:
        red("Secret credentials may not be placed in model prompts.")

    if get(m, "contract.cui_required") is True and get(m, "contract.required_cmmc_status", "UNKNOWN") == "UNKNOWN":
        amber("Contract requires CUI handling but required CMMC status/level has not been recorded.")

    required_il = get(m, "environment.required_impact_level", "") or ""
    actual_il = get(m, "environment.actual_impact_level", "") or ""
    if required_il and required_il != actual_il:
        amber(f"Required impact level {required_il!r} does not match recorded environment {actual_il!r}.")

    for path, label in [
        ("mission.owner", "mission owner"),
        ("mission.use_case", "use case"),
        ("environment.authorized", "environment authorization"),
        ("security.threat_model_complete", "threat model"),
        ("security.rollback_defined", "rollback plan"),
        ("security.audit_enabled", "audit logging"),
    ]:
        value = get(m, path)
        if path in {"environment.authorized", "security.threat_model_complete", "security.rollback_defined", "security.audit_enabled"}:
            if value is not True:
                amber(f"Required build evidence missing: {label}.")
        elif not value:
            amber(f"Required build evidence missing: {label}.")

    if get(m, "mission.material_external_action") is True and get(m, "mission.human_approval_required") is True:
        if not get(m, "release.human_approval_record", ""):
            amber("Material external action requires a recorded human approval.")

    build_allowed = state == "GREEN"
    deploy_allowed = build_allowed and all(
        [
            get(m, "release.tests_passed") is True,
            get(m, "release.evals_passed") is True,
            get(m, "release.owner_approved") is True,
            bool(get(m, "release.version", "")),
            bool(get(m, "release.audit_receipt", "")),
        ]
    )

    if build_allowed and not deploy_allowed:
        reasons.append("Build preflight passes; deployment evidence is incomplete.")

    return {
        "state": state,
        "allow_build": build_allowed,
        "allow_deploy": deploy_allowed,
        "reasons": reasons,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: frontline_compliance_check.py <manifest.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"state": "RED", "allow_build": False, "allow_deploy": False, "reasons": [f"Manifest read/JSON error: {exc}"]}, indent=2))
        return 1

    result = evaluate(manifest)
    print(json.dumps(result, indent=2))

    # CI semantics: GREEN build state = success. AMBER/RED/BLACK fail closed.
    return 0 if result["allow_build"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
