import json
from pathlib import Path

import pytest

from research_lab import cl1_organoid_swarm as cos


def test_topology_is_bounded_and_nonphysical():
    topo = cos.topology()
    assert topo["physical_organoid"] is False
    assert topo["global_infrastructure_control"] is False
    assert "cl1-simulator" in {layer["id"] for layer in topo["layers"]}


def test_manifest_rejects_unapproved_host(tmp_path: Path):
    payload = {
        "schema": "gpt-doug-cl1-authorized-sources/v1",
        "allowed_hosts": ["docs.corticallabs.com"],
        "sources": [
            {"id": "bad", "url": "https://example.com/", "authority": "TEST"}
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not allowlisted"):
        cos.load_manifest(path)


def test_simulator_requires_sdk_or_returns_synthetic(monkeypatch, tmp_path: Path):
    if cos._physical_marker_present():
        pytest.skip("physical CL1 marker present; simulator coordinator intentionally refuses hardware")
    try:
        result = cos.simulator_snapshot(0.1, tmp_path / "sim.h5")
    except RuntimeError as exc:
        assert "cl-sdk" in str(exc)
    else:
        assert result["physical_hardware"] is False
        assert result["organoid_created"] is False
        assert result["biological_learning_claim"] is False
