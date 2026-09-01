"""Normalize free/open-source scanner output into XUNIA findings.

This module consumes bounded local evidence previews and produces defensive findings and
remediation guidance. It does not generate exploit payloads or bypass instructions.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Iterable

from xunia_security_executor import ExecutionEvidence


SEVERITIES = {"critical", "high", "medium", "low", "info"}


@dataclass(frozen=True)
class NormalizedFinding:
    fingerprint: str
    tool_id: str
    severity: str
    title: str
    resource: str
    description: str
    remediation: str
    references: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["references"] = list(self.references)
        return data


def _severity(value: Any, default: str = "medium") -> str:
    normalized = str(value or default).strip().lower()
    if normalized in {"warning", "warn"}:
        normalized = "medium"
    if normalized in {"error", "fatal"}:
        normalized = "high"
    return normalized if normalized in SEVERITIES else default


def _fingerprint(tool: str, title: str, resource: str, reference: str = "") -> str:
    material = "\0".join((tool, title.strip().lower(), resource.strip().lower(), reference.strip().lower())).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _json_payloads(text: str) -> list[Any]:
    text = text.strip()
    if not text:
        return []
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        payloads = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith(("{", "[")):
                continue
            try:
                payloads.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return payloads


def _finding(tool: str, severity: Any, title: Any, resource: Any, description: Any, remediation: str, reference: str = "") -> NormalizedFinding:
    clean_title = str(title or "Security finding")[:500]
    clean_resource = str(resource or "unknown")[:1000]
    clean_description = str(description or clean_title)[:8000]
    return NormalizedFinding(
        fingerprint=_fingerprint(tool, clean_title, clean_resource, reference),
        tool_id=tool,
        severity=_severity(severity),
        title=clean_title,
        resource=clean_resource,
        description=clean_description,
        remediation=remediation,
        references=(reference,) if reference else (),
    )


def _normalize_nuclei(payload: Any) -> Iterable[NormalizedFinding]:
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        info = item.get("info") if isinstance(item.get("info"), dict) else {}
        reference = str(item.get("template-id") or item.get("templateID") or "")
        yield _finding(
            "nuclei",
            info.get("severity"),
            info.get("name") or reference or "Nuclei finding",
            item.get("matched-at") or item.get("host") or "web target",
            info.get("description") or info.get("name"),
            "Confirm the affected component, apply the vendor or configuration fix, then run an authorized retest.",
            reference,
        )


def _normalize_trivy(payload: Any) -> Iterable[NormalizedFinding]:
    if not isinstance(payload, dict):
        return
    for result in payload.get("Results", []) or []:
        if not isinstance(result, dict):
            continue
        target = result.get("Target") or "source/image"
        for vuln in result.get("Vulnerabilities", []) or []:
            if not isinstance(vuln, dict):
                continue
            ref = str(vuln.get("VulnerabilityID") or "")
            package = f"{vuln.get('PkgName', '')} {vuln.get('InstalledVersion', '')}".strip()
            yield _finding(
                "trivy",
                vuln.get("Severity"),
                vuln.get("Title") or ref or "Dependency vulnerability",
                f"{target}: {package}".strip(),
                vuln.get("Description") or ref,
                "Upgrade or replace the affected package/image component to a fixed version and rebuild the artifact.",
                ref,
            )
        for misconfig in result.get("Misconfigurations", []) or []:
            if not isinstance(misconfig, dict):
                continue
            ref = str(misconfig.get("ID") or "")
            yield _finding(
                "trivy",
                misconfig.get("Severity"),
                misconfig.get("Title") or ref or "Configuration finding",
                target,
                misconfig.get("Description") or misconfig.get("Message"),
                "Correct the configuration according to the referenced control, review the diff, and rescan before deployment.",
                ref,
            )


def _normalize_grype(payload: Any) -> Iterable[NormalizedFinding]:
    if not isinstance(payload, dict):
        return
    for match in payload.get("matches", []) or []:
        if not isinstance(match, dict):
            continue
        vuln = match.get("vulnerability") if isinstance(match.get("vulnerability"), dict) else {}
        artifact = match.get("artifact") if isinstance(match.get("artifact"), dict) else {}
        ref = str(vuln.get("id") or "")
        resource = f"{artifact.get('name', '')} {artifact.get('version', '')}".strip()
        yield _finding(
            "grype",
            vuln.get("severity"),
            ref or "Package vulnerability",
            resource or "artifact",
            vuln.get("description") or ref,
            "Upgrade the affected artifact to a non-vulnerable version, regenerate the SBOM, and retest the build.",
            ref,
        )


def _normalize_gitleaks(payload: Any) -> Iterable[NormalizedFinding]:
    items = payload if isinstance(payload, list) else payload.get("findings", []) if isinstance(payload, dict) else []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("RuleID") or item.get("RuleId") or "secret")
        resource = f"{item.get('File', 'source')}:{item.get('StartLine', '')}".rstrip(":")
        yield _finding(
            "gitleaks",
            "high",
            item.get("Description") or f"Potential secret: {ref}",
            resource,
            "A credential-like value was detected in source history or working files.",
            "Validate the detection, revoke/rotate any exposed credential, remove it from source/history as appropriate, and store secrets in a dedicated secret store.",
            ref,
        )


def _normalize_semgrep(payload: Any) -> Iterable[NormalizedFinding]:
    if not isinstance(payload, dict):
        return
    for item in payload.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
        start = item.get("start") if isinstance(item.get("start"), dict) else {}
        ref = str(item.get("check_id") or "")
        resource = f"{item.get('path', 'source')}:{start.get('line', '')}".rstrip(":")
        yield _finding(
            "semgrep",
            extra.get("severity"),
            extra.get("message") or ref or "Static analysis finding",
            resource,
            extra.get("message") or ref,
            "Review the flagged code path, apply the secure coding fix recommended by the rule, add a regression test, and rerun static analysis.",
            ref,
        )


def _normalize_checkov(payload: Any) -> Iterable[NormalizedFinding]:
    if not isinstance(payload, dict):
        return
    results = payload.get("results") if isinstance(payload.get("results"), dict) else {}
    for item in results.get("failed_checks", []) or []:
        if not isinstance(item, dict):
            continue
        ref = str(item.get("check_id") or "")
        yield _finding(
            "checkov",
            item.get("severity") or "medium",
            item.get("check_name") or ref or "Infrastructure-as-code finding",
            item.get("file_path") or "IaC",
            item.get("guideline") or item.get("check_name") or ref,
            "Update the infrastructure-as-code definition to satisfy the failed control, review the plan, and rescan before applying infrastructure changes.",
            ref,
        )


def _normalize_prowler(payload: Any) -> Iterable[NormalizedFinding]:
    items = payload if isinstance(payload, list) else payload.get("findings", []) if isinstance(payload, dict) else []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("Status") or item.get("status") or "").upper()
        if status in {"PASS", "PASSED", "COMPLIANT"}:
            continue
        ref = str(item.get("CheckID") or item.get("check_id") or "")
        yield _finding(
            "prowler",
            item.get("Severity") or item.get("severity"),
            item.get("CheckTitle") or item.get("title") or ref or "Cloud posture finding",
            item.get("ResourceId") or item.get("resource") or "cloud resource",
            item.get("Message") or item.get("description") or ref,
            "Apply the least-privilege or configuration correction for the affected cloud resource, review impact, and rerun the cloud posture check.",
            ref,
        )


NORMALIZERS = {
    "nuclei": _normalize_nuclei,
    "trivy": _normalize_trivy,
    "grype": _normalize_grype,
    "gitleaks": _normalize_gitleaks,
    "semgrep": _normalize_semgrep,
    "checkov": _normalize_checkov,
    "prowler": _normalize_prowler,
}


def normalize_evidence(evidence: ExecutionEvidence) -> list[NormalizedFinding]:
    if evidence.status not in {"COMPLETED", "FAILED"}:
        return []
    normalizer = NORMALIZERS.get(evidence.tool_id)
    if normalizer is None:
        return []
    findings: dict[str, NormalizedFinding] = {}
    for payload in _json_payloads(evidence.stdout_preview):
        for finding in normalizer(payload) or []:
            findings[finding.fingerprint] = finding
    return list(findings.values())
