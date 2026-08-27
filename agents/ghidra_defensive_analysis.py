"""Defensive Ghidra reverse-engineering bridge for GPT-DOUG-LLM / VA3LM.

This module ingests analysis metadata produced from binaries the operator is authorized
to inspect. It deliberately does not generate exploits, payloads, persistence, credential
theft, destructive actions, or third-party execution instructions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
import re

MODE = "DEFENSIVE_AUTHORIZED_BINARIES_ONLY"
SOURCE_REPOSITORY = "https://github.com/sonoxo/ghidraGPTDougLLMXYRA"
ANALYSIS_ENGINE = "Ghidra"
ONTOLOGY_CONTRACT_PATH = "foundry/ontology/ghidra-defense-ontology.json"

PROHIBITED_CAPABILITIES = (
    "exploit-generation",
    "payload-generation",
    "credential-theft",
    "destructive-action",
    "persistence-deployment",
    "third-party-execution",
    "autonomous-offensive-action",
)


@dataclass(frozen=True)
class ReverseEngineeringFinding:
    finding_id: str
    finding_type: str
    summary: str
    confidence: float
    function_name: str | None = None
    address: str | None = None
    technique_id: str | None = None


def build_ghidra_stack_config() -> dict[str, Any]:
    """Return the bounded integration contract for the Ghidra analysis stack."""
    return {
        "engine": ANALYSIS_ENGINE,
        "sourceRepository": SOURCE_REPOSITORY,
        "mode": MODE,
        "operation": "STATIC_ANALYSIS_AND_EVIDENCE_INGEST",
        "networkExecutionRequired": False,
        "humanReviewRequired": True,
        "ontologyContract": ONTOLOGY_CONTRACT_PATH,
        "ontologyBindings": {
            "artifact": "BinaryArtifact",
            "session": "ReverseEngineeringSession",
            "function": "FunctionObservation",
            "finding": "ReverseEngineeringFinding",
            "hypothesis": "VulnerabilityHypothesis",
            "asset": "Asset",
            "technique": "AttackTechnique",
            "incident": "Incident",
            "evidence": "Evidence",
        },
        "prohibitedCapabilities": list(PROHIBITED_CAPABILITIES),
        "guardrails": {
            "authorizedBinariesOnly": True,
            "analysisOnly": True,
            "exploitGeneration": False,
            "payloadGeneration": False,
            "thirdPartyExecution": False,
            "humanApprovalForIncidentActions": True,
            "rawBinaryDefault": "REMAIN_WITH_OWNER",
        },
    }


def normalize_ghidra_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a defensive Ghidra report into ontology-ready records.

    Expected input is metadata/evidence exported from an authorized Ghidra analysis job.
    Raw binary bytes are intentionally not required by this bridge.
    """
    sha256 = str(report.get("sha256", "")).lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("report.sha256 must be a 64-character hexadecimal SHA-256")

    artifact_id = str(report.get("artifactId") or f"binary:{sha256}")
    functions_raw = report.get("functions", [])
    findings_raw = report.get("findings", [])
    if not isinstance(functions_raw, list) or not isinstance(findings_raw, list):
        raise ValueError("functions and findings must be lists")

    functions: list[dict[str, Any]] = []
    for index, item in enumerate(functions_raw, start=1):
        if not isinstance(item, Mapping):
            continue
        functions.append({
            "functionId": str(item.get("functionId") or f"{artifact_id}:function:{index}"),
            "artifactId": artifact_id,
            "name": str(item.get("name", "")),
            "address": str(item.get("address", "")),
            "callingConvention": str(item.get("callingConvention", "")),
            "decompiled": bool(item.get("decompiled", False)),
        })

    findings: list[dict[str, Any]] = []
    for index, item in enumerate(findings_raw, start=1):
        if not isinstance(item, Mapping):
            continue
        confidence = float(item.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        finding = ReverseEngineeringFinding(
            finding_id=str(item.get("findingId") or f"{artifact_id}:finding:{index}"),
            finding_type=str(item.get("findingType", "OBSERVATION")),
            summary=str(item.get("summary", "")),
            confidence=confidence,
            function_name=str(item["functionName"]) if item.get("functionName") is not None else None,
            address=str(item["address"]) if item.get("address") is not None else None,
            technique_id=str(item["techniqueId"]) if item.get("techniqueId") is not None else None,
        )
        record = asdict(finding)
        record["artifactId"] = artifact_id
        record["reviewState"] = "UNDER_REVIEW"
        findings.append(record)

    return {
        "mode": MODE,
        "artifact": {
            "artifactId": artifact_id,
            "sha256": sha256,
            "name": str(report.get("name", "")),
            "format": str(report.get("format", "")),
            "architecture": str(report.get("architecture", "")),
            "authorizationScope": str(report.get("authorizationScope", "AUTHORIZED_ANALYSIS")),
        },
        "functions": functions,
        "findings": findings,
        "evidence": {
            "source": ANALYSIS_ENGINE,
            "sourceRepository": SOURCE_REPOSITORY,
            "analysisVersion": str(report.get("analysisVersion", "")),
            "sessionId": str(report.get("sessionId", "")),
        },
        "ontologyBindings": build_ghidra_stack_config()["ontologyBindings"],
        "guardrails": build_ghidra_stack_config()["guardrails"],
    }
