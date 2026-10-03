from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path("the-black-house/layers/vendetta/defensive_arsenal.py")
spec = importlib.util.spec_from_file_location("vendetta_defensive_arsenal", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_score_event_caps_and_labels_critical() -> None:
    result = module.score_event(
        {
            "event_type": "ransomware_indicator",
            "repeat_count": 20,
            "critical_asset": True,
        }
    )
    assert result["score"] == 100
    assert result["severity"] == "critical"
    assert result["recommended_action"] == "human_review"


def test_load_jsonl_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    payloads = [
        {"event_type": "auth_failure", "repeat_count": 2},
        {"event_type": "file_integrity_change", "critical_asset": True},
    ]
    path.write_text("\n".join(json.dumps(item) for item in payloads) + "\n", encoding="utf-8")
    assert module.load_jsonl(path) == payloads


def test_blackbox_sha256(capsys, tmp_path: Path) -> None:
    path = tmp_path / "evidence.txt"
    path.write_text("vendetta", encoding="utf-8")
    module.blackbox(path)
    output = json.loads(capsys.readouterr().out)
    assert output["weapon"] == "BLACKBOX"
    assert len(output["evidence"]["sha256"]) == 64


def test_airlock_is_plan_only(capsys) -> None:
    module.airlock("INC-001", True)
    output = json.loads(capsys.readouterr().out)
    assert output["execution"] == "PLAN_ONLY"
    assert output["requires_human_approval"] is True


def test_rewind_is_plan_only(capsys) -> None:
    module.rewind("INC-002")
    output = json.loads(capsys.readouterr().out)
    assert output["execution"] == "PLAN_ONLY"
    assert output["requires_human_approval"] is True
