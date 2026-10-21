"""Defensive offline REA multi-host evidence checks."""
import json
from pathlib import Path
import shutil

import pytest

from gpt_chaos.rea_swarm import execute, make_plan
from gpt_chaos.rea_federation import verify_manifests
from tests.test_rea_swarm import fake_rea


def fixture_manifest(tmp_path, monkeypatch):
    source, root = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    root.mkdir()
    fake_rea(tmp_path, monkeypatch, "import json;print(json.dumps({'kind':'mock'}))")
    report = execute(make_plan([str(source)], "javascript", str(root)), authorized=True)
    assert report["state"] == "PASS"
    return Path(report["output_directory"]) / "manifest.json"


def test_single_and_two_host_bundles(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    portable = tmp_path / "approved-copy"
    shutil.copytree(m.parent, portable)
    result = verify_manifests([str(m), str(portable / "manifest.json")])
    assert result["integrity"] == "VERIFIED"
    assert result["validated_jobs"] == 2 and result["remote_requests"] == 0


def test_tampering_detected(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    (m.parent / "01.json").write_text('{"changed":true}')
    result = verify_manifests([str(m)])
    assert result["integrity"] == "BLOCKED"
    assert "mismatch" in result["manifests"][0]["reason"]


def test_evidence_symlink_denied(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    evidence = m.parent / "01.json"
    target = tmp_path / "other.json"
    evidence.rename(target)
    evidence.symlink_to(target)
    assert verify_manifests([str(m)])["integrity"] == "BLOCKED"


def test_manifest_symlink_denied(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    link = tmp_path / "alias.json"
    link.symlink_to(m)
    assert verify_manifests([str(link)])["integrity"] == "BLOCKED"


def test_path_traversal_refused(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    content = json.loads(m.read_text())
    content["results"][0]["evidence"] = "../../leak"
    m.write_text(json.dumps(content))
    assert verify_manifests([str(m)])["integrity"] == "BLOCKED"


def test_blocked_task_partial(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    data = json.loads(m.read_text())
    data["results"] = [{"id": "01", "state": "BLOCKED", "reason": "failed"}]
    data["state"] = "BLOCKED"
    m.write_text(json.dumps(data))
    assert verify_manifests([str(m)])["integrity"] == "PARTIAL"


def test_invalid_inventory_and_oversize(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    data = json.loads(m.read_text())
    data["results"] = [{}]
    m.write_text(json.dumps(data))
    assert verify_manifests([str(m)])["integrity"] == "BLOCKED"
    m.write_bytes(b" " * (1024 * 1024 + 1))
    assert verify_manifests([str(m)])["integrity"] == "BLOCKED"


def test_duplicate_paths_rejected(tmp_path, monkeypatch):
    m = fixture_manifest(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        verify_manifests([str(m), str(m)])
