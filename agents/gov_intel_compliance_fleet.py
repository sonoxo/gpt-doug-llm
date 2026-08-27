#!/usr/bin/env python3
"""Government Intelligence Readiness Fleet for ZYRA.

This deterministic fleet assigns specialist subagents to Virginia and federal
control domains. It measures repository evidence, emits a command report, and
refuses to transform source-code success into external authorization claims.

No network access, target interaction, credential use, or external action is
performed by this module.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASELINE = Path("intel/compliance/government-intelligence-readiness.json")
POAM = Path("intel/compliance/poam.json")
REPORT_JSON = Path("intel/compliance/government-intelligence-audit.json")
REPORT_MD = Path("intel/compliance/government-intelligence-audit.md")


class GovernmentIntelError(RuntimeError):
    """Raised when government-intelligence readiness evidence is invalid."""


@dataclass(frozen=True)
class Finding:
    control: str
    state: str
    evidence: tuple[str, ...]
    gaps: tuple[str, ...] = ()
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "control": self.control,
            "state": self.state,
            "evidence": list(self.evidence),
            "gaps": list(self.gaps),
            "note": self.note,
        }


class EvidenceContext:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def path(self, relative: str) -> Path:
        return self.root / relative

    def exists(self, relative: str) -> bool:
        return self.path(relative).is_file()

    def text(self, relative: str) -> str:
        try:
            return self.path(relative).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            return ""

    def has_all(self, paths: list[str]) -> tuple[list[str], list[str]]:
        present = [path for path in paths if self.exists(path)]
        missing = [path for path in paths if not self.exists(path)]
        return present, missing


class Subagent:
    name = "BASE"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        raise NotImplementedError


class VirginiaSEC530Subagent(Subagent):
    name = "VIRGINIA-SEC530-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        required = [
            "intel/compliance/system-security-plan.md",
            "intel/compliance/access-control-plan.md",
            "intel/compliance/incident-response-plan.md",
            "intel/compliance/configuration-management-plan.md",
            "intel/compliance/contingency-plan.md",
            "intel/compliance/cryptography-and-key-management-plan.md",
            "intel/compliance/poam.json",
            ".github/workflows/security-gate.yml",
        ]
        present, missing = ctx.has_all(required)
        return Finding(
            "VIRGINIA_SEC530_01_2",
            "PARTIAL_EVIDENCE" if not missing else "SOURCE_GAP",
            tuple(present),
            tuple(missing),
            "Repository evidence supports control engineering; Commonwealth deployment evidence remains environment-specific.",
        )


class VirginiaAISubagent(Subagent):
    name = "VIRGINIA-AI-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        required = [
            "intel/compliance/ai-governance-plan.md",
            "agents/virginia_intel_gate.py",
            "intel/policy/legal-facts-framework.json",
        ]
        present, missing = ctx.has_all(required)
        return Finding(
            "VIRGINIA_AI_GOVERNANCE",
            "PARTIAL_EVIDENCE" if not missing else "SOURCE_GAP",
            tuple(present),
            tuple(missing),
            "Archer/Planview and agency approval evidence is required only when the deployment/use case triggers Commonwealth governance.",
        )


class NIST80053Subagent(Subagent):
    name = "NIST-80053-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        workflow = ctx.text(".github/workflows/security-gate.yml").lower()
        indicators = {
            "tests": "pytest" in workflow,
            "lint": "ruff" in workflow,
            "static_security": "bandit" in workflow,
            "dependency_audit": "pip-audit" in workflow,
            "sbom": "cyclonedx" in workflow and "sbom" in workflow,
        }
        gaps = tuple(name for name, ok in indicators.items() if not ok)
        evidence = [".github/workflows/security-gate.yml"] if workflow else []
        return Finding(
            "NIST_SP_800_53_REV5",
            "PARTIAL_EVIDENCE" if not gaps else "SOURCE_GAP",
            tuple(evidence),
            gaps,
            "A control catalog is not a system authorization; organizational and deployment controls require separate evidence.",
        )


class CUI171Subagent(Subagent):
    name = "CUI-800171-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        evidence = tuple(
            path
            for path in [
                "intel/compliance/system-security-plan.md",
                "intel/compliance/poam.json",
                "intel/compliance/access-control-plan.md",
                "intel/compliance/incident-response-plan.md",
            ]
            if ctx.exists(path)
        )
        return Finding(
            "NIST_SP_800_171_REV3",
            "EXTERNAL_OR_DEPLOYMENT_EVIDENCE_REQUIRED",
            evidence,
            ("CUI boundary and contractual scope are not established by repository code.",),
            "Activate only if CUI is processed, stored, transmitted, or protected by the deployment.",
        )


class FedRAMPSubagent(Subagent):
    name = "FEDRAMP-2026-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        evidence = tuple(
            path
            for path in [
                "intel/compliance/system-security-plan.md",
                "intel/compliance/poam.json",
                ".github/workflows/security-gate.yml",
            ]
            if ctx.exists(path)
        )
        return Finding(
            "FEDRAMP_REV5_2026",
            "EXTERNAL_AUTHORIZATION_REQUIRED",
            evidence,
            (
                "Applicable FedRAMP class/path not selected.",
                "Assessment and accepted authorization evidence are outside repository scope.",
                "Continuous-monitoring evidence is deployment specific.",
            ),
            "Repository controls may support a future package but cannot confer FedRAMP authorization.",
        )


class FIPSSubagent(Subagent):
    name = "FIPS-1403-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        evidence = (
            ("intel/compliance/cryptography-and-key-management-plan.md",)
            if ctx.exists("intel/compliance/cryptography-and-key-management-plan.md")
            else ()
        )
        return Finding(
            "FIPS_140_3",
            "EXTERNAL_OR_RUNTIME_EVIDENCE_REQUIRED",
            evidence,
            ("CMVP certificate/inherited validated module and runtime configuration are deployment evidence.",),
            "A library name or algorithm choice is not FIPS validation.",
        )


class CJISSubagent(Subagent):
    name = "CJIS-6.1-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        evidence = tuple(
            path
            for path in [
                "intel/compliance/access-control-plan.md",
                "intel/compliance/incident-response-plan.md",
                "intel/compliance/cryptography-and-key-management-plan.md",
            ]
            if ctx.exists(path)
        )
        return Finding(
            "FBI_CJIS_SECURITY_POLICY_6_1",
            "EXTERNAL_OR_DEPLOYMENT_EVIDENCE_REQUIRED",
            evidence,
            ("CJI scope, applicable CSA requirements, agreements, personnel/access controls, and audit evidence are deployment-specific.",),
            "Activate only when the system accesses, processes, stores, transmits, or protects CJI.",
        )


class AIRiskSubagent(Subagent):
    name = "AI-RISK-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        required = [
            "intel/compliance/ai-governance-plan.md",
            "agents/virginia_intel_gate.py",
            "agents/ontology_master_lock.py",
            "agents/glassonion_layer.py",
        ]
        present, missing = ctx.has_all(required)
        return Finding(
            "NIST_AI_RMF_AND_GAI_PROFILE",
            "PARTIAL_EVIDENCE" if not missing else "SOURCE_GAP",
            tuple(present),
            tuple(missing),
            "Human command review, provenance, bounded tools, and evidence locks are present; use-case TEVV remains deployment-specific.",
        )


class EvidencePackSubagent(Subagent):
    name = "EVIDENCE-PACK-INTEL"

    def inspect(self, ctx: EvidenceContext) -> Finding:
        baseline = _load_json(ctx.path(BASELINE))
        required = list(baseline.get("requiredCommandArtifacts") or [])
        present, missing = ctx.has_all(required)
        return Finding(
            "COMMAND_EVIDENCE_PACK",
            "IMPLEMENTED_EVIDENCE_PRESENT" if not missing else "SOURCE_GAP",
            tuple(present),
            tuple(missing),
            "This finding covers repository artifacts only, not deployment authorization.",
        )


FLEET: tuple[type[Subagent], ...] = (
    VirginiaSEC530Subagent,
    VirginiaAISubagent,
    NIST80053Subagent,
    CUI171Subagent,
    FedRAMPSubagent,
    FIPSSubagent,
    CJISSubagent,
    AIRiskSubagent,
    EvidencePackSubagent,
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GovernmentIntelError(f"cannot read intelligence artifact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GovernmentIntelError(f"expected JSON object: {path}")
    return value


def audit(root: str | Path) -> dict[str, Any]:
    ctx = EvidenceContext(root)
    baseline = _load_json(ctx.path(BASELINE))
    if baseline.get("framework") != "ZYRA GOVERNMENT INTELLIGENCE READINESS COMMAND":
        raise GovernmentIntelError("unexpected government-intelligence baseline")
    findings = [agent_type().inspect(ctx) for agent_type in FLEET]
    source_gaps = [finding for finding in findings if finding.state == "SOURCE_GAP"]
    external_gates = [
        finding
        for finding in findings
        if finding.state in {"EXTERNAL_AUTHORIZATION_REQUIRED", "EXTERNAL_OR_RUNTIME_EVIDENCE_REQUIRED", "EXTERNAL_OR_DEPLOYMENT_EVIDENCE_REQUIRED"}
    ]
    command_state = "SOURCE_READY_WITH_EXTERNAL_GATES" if not source_gaps else "SOURCE_GAPS_PRESENT"
    return {
        "framework": baseline["framework"],
        "version": baseline["version"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "commandState": command_state,
        "selfCertification": False,
        "counts": {
            "subagents": len(findings),
            "sourceGaps": len(source_gaps),
            "externalOrDeploymentGates": len(external_gates),
        },
        "findings": [finding.as_dict() for finding in findings],
        "commandConclusion": (
            "Repository intelligence controls are source-ready; named external/deployment gates remain before any baseline-specific authorization claim."
            if not source_gaps
            else "Repository intelligence controls still contain source-code/documentation gaps."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ZYRA Government Intelligence Readiness Audit",
        "",
        f"Command state: **{report['commandState']}**",
        f"Subagents: {report['counts']['subagents']}",
        f"Source gaps: {report['counts']['sourceGaps']}",
        f"External/deployment gates: {report['counts']['externalOrDeploymentGates']}",
        "",
        "| Intelligence subagent/control | State | Evidence | Gaps |",
        "|---|---|---|---|",
    ]
    for item in report["findings"]:
        evidence = ", ".join(item["evidence"]) or "none"
        gaps = "; ".join(item["gaps"]) or "none"
        lines.append(f"| {item['control']} | {item['state']} | {evidence} | {gaps} |")
    lines.extend(
        [
            "",
            "## Command conclusion",
            report["commandConclusion"],
            "",
            "Passing this audit is not FedRAMP authorization, CJIS acceptance, FIPS validation, CUI authorization, or Commonwealth deployment approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(root: str | Path) -> dict[str, Any]:
    ctx = EvidenceContext(root)
    report = audit(root)
    json_path = ctx.path(REPORT_JSON)
    md_path = ctx.path(REPORT_MD)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return report


def command_status(root: str | Path) -> str:
    report = audit(root)
    symbol = "✅" if report["counts"]["sourceGaps"] == 0 else "❌"
    lines = [
        f"🛰️ GOVERNMENT INTELLIGENCE READINESS // {report['commandState']} {symbol}",
        f"Subagents: {report['counts']['subagents']}",
        f"Source gaps: {report['counts']['sourceGaps']}",
        f"External/deployment gates: {report['counts']['externalOrDeploymentGates']}",
    ]
    for item in report["findings"]:
        lines.append(f"- {item['control']}: {item['state']}")
    lines.append("COMMAND RULE: report the exact baseline and evidence state; never substitute a generic government-compliant claim.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="ZYRA Government Intelligence Readiness Fleet")
    parser.add_argument("action", choices=["status", "audit", "strict-source"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        if args.action == "status":
            print(command_status(args.root))
            return 0
        report = write_report(args.root)
        print(command_status(args.root))
        print(f"Audit JSON: {REPORT_JSON}")
        print(f"Audit brief: {REPORT_MD}")
        if args.action == "strict-source" and report["counts"]["sourceGaps"]:
            return 2
        return 0
    except GovernmentIntelError as exc:
        print(f"GOVERNMENT INTELLIGENCE READINESS // GATE HOLD ❌ // {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
