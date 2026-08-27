import json
from pathlib import Path

import pytest

from agents.va3lm_redhat_defense import CONTROL_CATALOG, audit_host
from agents.va3lm_redhat_ontology import (
    Va3lmOntologyError,
    gaps,
    graph,
    load_verified,
    run_lock,
    status,
)

ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path: Path) -> Path:
    source = ROOT / "intel/va3lm/NSA-QTFY-20260826.json"
    target = tmp_path / "intel/va3lm/NSA-QTFY-20260826.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return tmp_path


def test_control_catalog_covers_core_red_hat_defenses():
    ids = {item["id"] for item in CONTROL_CATALOG}
    assert {
        "VA3LM-RH-PATCH",
        "VA3LM-RH-WEB",
        "VA3LM-RH-SEGMENT",
        "VA3LM-RH-HUNT",
        "VA3LM-RH-SELINUX",
        "VA3LM-RH-FIREWALL",
        "VA3LM-RH-SSH",
        "VA3LM-RH-AUDIT",
        "VA3LM-RH-INTEGRITY",
        "VA3LM-RH-ALLOWLIST",
        "VA3LM-RH-JOURNAL",
        "VA3LM-RH-TIME",
    }.issubset(ids)


def test_host_audit_is_fixed_local_defense_only():
    result = audit_host()
    assert result["mode"] == "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"
    guardrails = result["guardrails"]
    assert guardrails["remoteScanning"] is False
    assert guardrails["exploitExecution"] is False
    assert guardrails["retaliation"] is False
    assert guardrails["arbitraryShell"] is False
    assert guardrails["automaticContainment"] is False
    assert guardrails["humanReviewRequired"] is True
    assert result["sourceIntel"]["sourceId"] == "NSA-QTFY-2026-08-26"


def test_va3lm_lock_builds_verified_ontology(tmp_path):
    root = _workspace(tmp_path)
    manifest = run_lock(root)
    assert manifest["locked"] is True
    assert manifest["publicationState"] == "LOCKED_DEFENSIVE_INTELLIGENCE"
    assert all(item["status"] == "PASS" for item in manifest["subagents"])

    loaded, evidence, ontology = load_verified(root)
    assert loaded["lockId"] == manifest["lockId"]
    assert ontology["framework"] == "VA3LM RED HAT DEFENSE ONTOLOGY"
    assert len(ontology["objects"]) >= 20
    assert len(ontology["links"]) >= 20
    assert evidence["guardrails"]["remoteScanning"] is False
    assert "LOCK VERIFIED" in status(root)
    assert "RecommendationImplementedByControl" in graph(root)
    assert "defensive posture evidence" in gaps(root)


def test_va3lm_lock_rejects_tampered_evidence(tmp_path):
    root = _workspace(tmp_path)
    run_lock(root)
    evidence = root / "intel/va3lm/redhat-defense-evidence.json"
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["guardrails"]["remoteScanning"] = True
    evidence.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Va3lmOntologyError, match="hash mismatch"):
        load_verified(root)
