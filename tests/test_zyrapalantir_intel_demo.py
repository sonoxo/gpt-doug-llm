import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "zyrapalantir_intel_demo.py"


def load_module():
    spec = importlib.util.spec_from_file_location("zyrapalantir_intel_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_synthetic_scenario_correlates_independent_sources(monkeypatch, tmp_path):
    mod = load_module()
    scenario = json.loads((ROOT / "demo" / "zyrapalantir-intel-scenario.json").read_text())
    ontology = json.loads((ROOT / "safety-shield" / "ontology" / "zyrapalantir-intel-demo.json").read_text())
    mod.validate_synthetic(scenario, ontology)

    state = tmp_path / "defense-profile.json"
    state.write_text('{"active": true}\n')
    monkeypatch.setattr(mod, "STATE_PATH", state)

    result = mod.correlate(scenario)
    assert result["classification"] == "SYNTHETIC//UNCLASSIFIED"
    assert result["defense_profile_active"] is True
    assert result["correlation"]["independent_sources"] == 2
    assert "indicator-domain-01" in result["correlation"]["corroborated_indicators"]
    assert result["assessment"] == "REVIEW_REQUIRED"
    assert result["automatic_external_action_taken"] is False
    assert result["analyst_approval_required"] is True


def test_non_synthetic_indicator_is_rejected():
    mod = load_module()
    scenario = json.loads((ROOT / "demo" / "zyrapalantir-intel-scenario.json").read_text())
    ontology = json.loads((ROOT / "safety-shield" / "ontology" / "zyrapalantir-intel-demo.json").read_text())
    scenario["indicators"][0]["synthetic"] = False

    with pytest.raises(SystemExit):
        mod.validate_synthetic(scenario, ontology)
