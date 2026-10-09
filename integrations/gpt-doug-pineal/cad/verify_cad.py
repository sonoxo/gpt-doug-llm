"""Executable CAD requirements for GPT-Doug-PINEAL architectural assembly."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_assembly_contains_distinct_spatial_layers():
    from pineal_cad import build_model
    parts = build_model()
    layers = {part.layer for part in parts}
    assert len(parts) >= 40
    assert {"FOUNDATION", "PINEAL-CORE", "GPU-LLM", "ONTOLOGY-MEMORY",
            "CELL-ATLAS", "NEURAL-RESEARCH", "KRAKEN-CONDUITS",
            "ZYRA-SHIELD", "PATENT-NETWORK"} <= layers
    assert all(part.shape.isValid() and part.shape.Volume() > 0 for part in parts)
    assert all(part.name and part.layer and len(part.rgb) == 3 for part in parts)


def test_export_opens_as_3d_cad_and_viewer(tmp_path):
    import ezdxf
    import trimesh
    from pineal_cad import export_model
    outputs = export_model(tmp_path, tolerance=1.25)
    assert all(Path(f).exists() and Path(f).stat().st_size > 1024 for f in outputs.values())
    assert {"step", "dxf", "stl", "glb", "manifest"} <= outputs.keys()
    assert Path(outputs["step"]).read_text(errors="replace").startswith("ISO-10303-21;")
    drawing = ezdxf.readfile(outputs["dxf"])
    assert sum(1 for ent in drawing.modelspace() if ent.dxftype() == "3DFACE") > 1000
    assert "PINEAL-CORE" in drawing.layers
    assert "ZYRA-SHIELD" in drawing.layers
    mesh = trimesh.load(outputs["glb"], force="scene")
    assert len(mesh.geometry) >= 40
    assert all(g.bounds[0][2] >= -1 for g in mesh.geometry.values())


def test_manifest_records_conceptual_not_human_neural_device(tmp_path):
    import json
    from pineal_cad import export_model
    outputs = export_model(tmp_path, tolerance=2.0)
    meta = json.loads(Path(outputs["manifest"]).read_text())
    assert meta["units"] == "mm"
    assert meta["status"] == "conceptual_nonbiological_software_architecture"
    assert meta["hardware_verified"] is False
    assert meta["live_external_feeds"] is False
    assert len(meta["layers"]) >= 9
