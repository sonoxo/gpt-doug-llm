from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "maven_live_sync.py"
spec = importlib.util.spec_from_file_location("maven_live_sync", MODULE_PATH)
assert spec and spec.loader
maven_live_sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maven_live_sync)
SyncError = maven_live_sync.SyncError
sync = maven_live_sync.sync


def base_graph() -> dict:
    return {
        "meta": {"name": "Maven Ontology", "version": "1.0"},
        "governance": {"actionModes": ["recommend", "simulate", "approved"]},
        "objectTypes": ["Source"],
        "relationTypes": [],
        "nodes": [
            {
                "id": "maven:source",
                "label": "Source",
                "objectType": "Source",
                "type": "knowledge",
                "status": "verified",
                "confidence": 0.95,
            }
        ],
        "links": [],
    }


def approved_export() -> dict:
    return {
        "schemaVersion": "maven-export/1.0",
        "source": {
            "system": "Palantir Maven",
            "exportId": "export-001",
            "uri": "palantir://maven/example/export-001",
            "generatedAt": "2026-09-10T15:00:00Z",
        },
        "approval": {
            "status": "approved",
            "scope": "ontology-sync",
            "approvedBy": "operator@example",
            "approvedAt": "2026-09-10T15:01:00Z",
        },
        "nodes": [
            {
                "id": "maven:mission:demo",
                "label": "Demo Mission",
                "objectType": "Mission",
                "type": "governance",
                "status": "candidate",
                "confidence": 0.7,
            },
            {
                "id": "maven:approval:demo",
                "label": "Demo Approval",
                "objectType": "Approval",
                "type": "governance",
                "status": "verified",
                "confidence": 0.95,
            },
            {
                "id": "maven:action:demo",
                "label": "Demo Action",
                "objectType": "Action",
                "type": "agent",
                "status": "candidate",
                "confidence": 0.6,
                "mode": "approved",
                "approvalId": "maven:approval:demo",
            },
        ],
        "links": [
            ["maven:mission:demo", "maven:action:demo", "RECOMMENDS"],
            {
                "source": "maven:action:demo",
                "target": "maven:approval:demo",
                "relation": "requires",
            },
        ],
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run_sync(tmp_path: Path, export: dict) -> tuple[dict, Path, Path]:
    source = tmp_path / "approved.json"
    target = tmp_path / "ontology.json"
    audit = tmp_path / "sync-log.json"
    write_json(source, export)
    write_json(target, base_graph())
    result = sync(source, target, audit)
    return result, target, audit


def test_approved_export_merges_with_provenance(tmp_path: Path) -> None:
    result, target, audit = run_sync(tmp_path, approved_export())
    graph = json.loads(target.read_text())
    imported = next(node for node in graph["nodes"] if node["id"] == "maven:mission:demo")

    assert result["ok"] is True
    assert imported["provenance"]["sourceSystem"] == "Palantir Maven"
    assert imported["provenance"]["exportId"] == "export-001"
    assert imported["provenance"]["approvedBy"] == "operator@example"
    assert ["maven:action:demo", "maven:approval:demo", "REQUIRES"] in graph["links"]
    assert json.loads(audit.read_text())["records"][0]["exportId"] == "export-001"


def test_unapproved_export_is_rejected_without_writes(tmp_path: Path) -> None:
    export = approved_export()
    export["approval"]["status"] = "pending"
    source = tmp_path / "pending.json"
    target = tmp_path / "ontology.json"
    audit = tmp_path / "sync-log.json"
    write_json(source, export)
    write_json(target, base_graph())
    before = target.read_text()

    with pytest.raises(SyncError, match="approval.status"):
        sync(source, target, audit)

    assert target.read_text() == before
    assert not audit.exists()


def test_approved_action_requires_approval_reference(tmp_path: Path) -> None:
    export = approved_export()
    action = next(node for node in export["nodes"] if node["objectType"] == "Action")
    action.pop("approvalId")
    with pytest.raises(SyncError, match="requires approvalId"):
        run_sync(tmp_path, export)


def test_approved_action_reference_must_resolve(tmp_path: Path) -> None:
    export = approved_export()
    action = next(node for node in export["nodes"] if node["objectType"] == "Action")
    action["approvalId"] = "maven:approval:missing"
    with pytest.raises(SyncError, match="references missing Approval"):
        run_sync(tmp_path, export)


def test_broken_link_is_rejected(tmp_path: Path) -> None:
    export = approved_export()
    export["links"].append(["maven:mission:demo", "maven:missing", "USES"])
    with pytest.raises(SyncError, match="broken link"):
        run_sync(tmp_path, export)


def test_reprocessing_same_export_is_idempotent(tmp_path: Path) -> None:
    result, target, audit = run_sync(tmp_path, approved_export())
    assert result["graphChanged"] is True
    graph_before = target.read_bytes()
    audit_before = audit.read_bytes()

    source = tmp_path / "approved.json"
    second = sync(source, target, audit)

    assert second["graphChanged"] is False
    assert second["auditChanged"] is False
    assert target.read_bytes() == graph_before
    assert audit.read_bytes() == audit_before


def test_missing_globe_position_is_deterministic(tmp_path: Path) -> None:
    export = approved_export()
    result, target, _ = run_sync(tmp_path, export)
    assert result["ok"]
    graph = json.loads(target.read_text())
    node = next(item for item in graph["nodes"] if item["id"] == "maven:mission:demo")
    first = (node["lat"], node["lon"])

    other = tmp_path / "second"
    _, target2, _ = run_sync(other, export)
    graph2 = json.loads(target2.read_text())
    node2 = next(item for item in graph2["nodes"] if item["id"] == "maven:mission:demo")
    assert (node2["lat"], node2["lon"]) == first
