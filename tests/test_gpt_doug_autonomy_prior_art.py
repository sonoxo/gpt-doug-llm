import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/uspto-adjacent-tesla-autonomous-vehicle-summon-family.json"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/gpt-doug-adjacent-autonomy-prior-art-v1.json"
BRIEF = ROOT / "intel/briefings/2026-09-12-tesla-autonomous-vehicle-summon-prior-art.md"


def load_cli():
    spec = importlib.util.spec_from_file_location(
        "gpt_doug_autonomy_prior_art", ROOT / "scripts/gpt_doug_autonomy_prior_art.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_exact_tesla_family_metadata_and_relationships():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert source["company"] == "Tesla, Inc."
    assert source["family_title"] == "AUTONOMOUS AND USER CONTROLLED VEHICLE SUMMON TO A TARGET"
    docs = {item["document_number"]: item for item in source["documents"]}
    assert set(docs) == {"US-20230176593-A1", "US-11567514-B2", "US-20200257317-A1"}
    assert docs["US-11567514-B2"]["prior_publication"] == "US-20200257317-A1"
    assert docs["US-11567514-B2"]["assignee"]["name"] == "Tesla, Inc."
    assert "Continuation" in docs["US-20230176593-A1"]["relationship"]


def test_visible_flow_is_preserved_as_architecture_watch():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert source["visible_flow"] == [
        "Receive Destination",
        "Receive Vision Data",
        "Determine Drivable Space",
        "Generate Occupancy Grid",
        "Determine Path Goal",
        "Navigate To Path Goal",
        "Check Arrival At Destination",
        "Complete Summon",
    ]
    assert source["architecture_watch"]["name"] == "civilian-autonomous-mobility-perception-planning-execution-loop"


def test_weaponization_and_unattended_vehicle_controls_are_blocked():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    controls = source["controls"]
    assert controls["allow_weapon_targeting_mapping"] is False
    assert controls["allow_hostile_engagement_mapping"] is False
    assert controls["allow_weapon_release_or_drone_swarm_control"] is False
    assert controls["allow_unattended_real_world_vehicle_command"] is False
    assert controls["require_human_authorization_for_any_real_world_mobility_action"] is True

    ontology = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    blocked = set(ontology["governed_actions"]["BLOCK"])
    assert {
        "map_destination_to_hostile_targeting",
        "weapon_target_selection",
        "weapons_release",
        "drone_swarm_attack_control",
        "hostile_pursuit_or_engagement",
        "unattended_real_world_vehicle_command",
    }.issubset(blocked)


def test_brief_and_cli_are_wired():
    assert BRIEF.exists()
    text = BRIEF.read_text(encoding="utf-8")
    assert "US-20230176593-A1" in text
    assert "US-11567514-B2" in text
    assert "US-20200257317-A1" in text
    assert "civilian" in text.lower()
    cli = load_cli()
    assert cli.doctor() == 0
