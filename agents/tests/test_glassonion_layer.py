from __future__ import annotations

import json
from pathlib import Path

from agents.glassonion_layer import build_brief, build_overlay
from agents.qtfy_advisory_intel import build_qtfy_defensive_plan

ROOT = Path(__file__).resolve().parents[2]


def _source() -> dict:
    return json.loads((ROOT / "intel/glassonion/DOJ-26-972.json").read_text(encoding="utf-8"))


def test_glassonion_overlay_crosslinks_locked_qtfy_refs() -> None:
    source = _source()
    base = build_qtfy_defensive_plan()["ontology"]
    overlay = build_overlay(source, base, "test-base-lock")

    assert overlay["baseMasterLockId"] == "test-base-lock"
    assert overlay["guardrails"]["baseOntologyImmutable"] is True
    assert overlay["guardrails"]["externalThirdPartyAction"] is False
    assert overlay["guardrails"]["offensiveReplication"] is False

    refs = {f"{item['objectType']}:{item['id']}" for item in overlay["objects"]}
    assert "PublicSource:DOJ-26-972" in refs
    assert "InfrastructureComponent:hardcoded-platform-domains" in refs
    assert "LegalDisruptionAction:evt-2026-08-26-doj-domain-seizure" in refs

    relationships = {(link["linkType"], link["from"], link["to"]) for link in overlay["links"]}
    assert (
        "SourceCrossReferencesAdvisory",
        "PublicSource:DOJ-26-972",
        "CyberAdvisory:JCSA-20260826-01",
    ) in relationships
    assert (
        "ThreatReportedEmployedBy",
        "ThreatProfile:QTFY",
        "Organization:nanjing-xinjiuwei",
    ) in relationships
    assert (
        "ToolFeedsTool",
        "ThreatTool:qscan",
        "ThreatTool:qtrouter",
    ) in relationships
    assert (
        "DisruptionReportedDisablesTool",
        "LegalDisruptionAction:evt-2026-08-26-doj-domain-seizure",
        "ThreatTool:qscan",
    ) in relationships


def test_glassonion_brief_preserves_claim_scope() -> None:
    source = _source()
    overlay = build_overlay(source, build_qtfy_defensive_plan()["ontology"], "test-base-lock")
    brief = build_brief(source, overlay)

    assert "DOJ 26-972" in brief
    assert "source claims, not independent Glass Onion attribution" in brief
    assert "does not authorize scanning or action against third-party infrastructure" in brief
    assert "Base ontology lock: test-base-lock" in brief
