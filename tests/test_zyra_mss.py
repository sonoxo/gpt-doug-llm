import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "safety-shield/ontology/zyra-mss-v1.json"
SWEEP = ROOT / "intel/sources/zyra-mss-patent-architecture-sweep-2026-09-12.json"
DOC = ROOT / "docs/ZYRA_MSS.md"


def load_cli():
    spec = importlib.util.spec_from_file_location("zyra_mss", ROOT / "scripts/zyra_mss.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_zyra_mss_ontology_is_bounded_and_human_authorized():
    data = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    assert data["ontology"] == "ZYRA_MSS_V1"
    assert data["logical_agent_fleet"]["count"] == 100
    assert data["logical_agent_fleet"]["agent_authority"] == "RECOMMEND_ONLY"
    assert data["logical_agent_fleet"]["automatic_external_action"] is False
    blocked = set(data["governed_actions"]["BLOCK"])
    assert {
        "autonomous_target_selection",
        "weapons_release",
        "weapon_or_drone_swarm_control",
        "hostile_engagement",
        "critical_infrastructure_disruption",
        "unattended_real_world_vehicle_command",
        "bypass_human_authorization",
    }.issubset(blocked)


def test_patent_sweep_is_provenance_aware_and_rate_limited():
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    assert sweep["primary_source"] == "https://ppubs.uspto.gov/basic/"
    assert sweep["research_method"]["logical_agent_count"] == 100
    assert sweep["research_method"]["network_concurrency_cap"] <= 8
    assert sweep["research_method"]["respect_rate_limits"] is True
    assert sweep["legal_and_research_controls"]["independent_design_required"] is True
    assert len(sweep["architecture_signals"]) >= 15


def test_docs_and_cli_are_wired():
    assert DOC.exists()
    shell = (ROOT / "scripts/zyrapalantir").read_text(encoding="utf-8")
    assert 'mss) shift; exec python3 "$ROOT/scripts/zyra_mss.py" "$@" ;;' in shell
    assert "|mss|" in shell
    cli = load_cli()
    assert cli.doctor() == 0
