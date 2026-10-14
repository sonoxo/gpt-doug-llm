from pathlib import Path

from research_lab import cl1_mitochondria as cm


def test_evidence_registry_truth_boundary():
    data = cm.load_evidence()
    assert data["status"] == "RESEARCH_ONLY"
    assert data["truth_boundary"]["cl1_device_access"] is False
    assert data["truth_boundary"]["platform_specific_mitochondria_scan_available"] is False


def test_model_is_reference_not_reconstruction():
    data = cm.model()
    assert data["device_specific_reconstruction"] is False
    assert data["hardware_connection"] is False
    ids = {item["id"] for item in data["components"]}
    assert {"outer_membrane", "inner_membrane", "cristae", "matrix", "mtdna", "atp_synthase", "micos"} <= ids


def test_html_is_self_contained_and_truthful(tmp_path: Path):
    text = cm.html_document()
    assert "Not a CL1 microscopy reconstruction" in text
    assert "CL1 public API exposes neural electrical activity" in text
    assert "<script" not in text.lower()
    assert "http://" not in text and "https://" not in text
