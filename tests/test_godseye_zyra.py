import json
from pathlib import Path

from godseye.zyra import zyra_status


def test_zyra_status_reads_mss_ontology(tmp_path: Path):
    path = tmp_path / "zyra.json"
    path.write_text(
        json.dumps(
            {
                "ontology": "ZYRA_MSS_V1",
                "mode": "HUMAN_AUTHORIZED_MISSION_SUPPORT",
                "logical_agent_fleet": {"count": 100, "agent_authority": "RECOMMEND_ONLY", "automatic_external_action": False},
                "governed_actions": {"BLOCK": ["autonomous_target_selection"]},
            }
        ),
        encoding="utf-8",
    )
    result = zyra_status(path=path)
    assert result["schema"] == "gpt-doug.zyra-status.v1"
    assert result["status"] == "ONLINE"
    assert result["ontology"] == "ZYRA_MSS_V1"
    assert result["logicalAgentCount"] == 100
    assert result["agentAuthority"] == "RECOMMEND_ONLY"
    assert result["automaticExternalAction"] is False
    assert result["provenance"] == [str(path)]


def test_zyra_status_degrades_when_ontology_missing(tmp_path: Path):
    result = zyra_status(path=tmp_path / "missing.json")
    assert result["status"] == "DEGRADED"
    assert result["partial"] is True
    assert result["errors"]
