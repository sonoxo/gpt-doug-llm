from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "maven-eco-fabric.py"


def load_module():
    spec = importlib.util.spec_from_file_location("maven_eco_fabric", MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_eco_fabric_snapshot_contract():
    module = load_module()
    snap = module.build_snapshot()

    assert snap["schema"] == "xunia.maven.eco-fabric.v1"
    assert snap["ecosystem"]["control_root"] == "sonoxo/gpt-doug-llm"
    assert snap["summary"]["core_planes"] == 8
    assert snap["summary"]["ai_layers"] == 6
    assert len({plane["id"] for plane in snap["planes"]}) == 8
    assert snap["authority"]["model_output_creates_execution_authority"] is False
    assert snap["authority"]["repository_membership_creates_external_authorization"] is False


def test_eco_fabric_routes_resolve():
    module = load_module()
    snap = module.build_snapshot()
    known = {p["id"] for p in snap["planes"]} | {d["id"] for d in snap["internal_divisions"]}

    for target in snap["domain_routing"].values():
        assert target in known
