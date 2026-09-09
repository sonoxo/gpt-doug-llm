import json
from pathlib import Path

from tools.validate_drone_security_ontology import validate

ONTOLOGY = Path("intel/drone-security/damn-vulnerable-drone-ontology.json")


def _load():
    return json.loads(ONTOLOGY.read_text(encoding="utf-8"))


def test_repository_ontology_is_valid():
    assert validate(_load()) == []


def test_guardrails_block_operational_drone_actions():
    guardrails = _load()["guardrails"]
    assert guardrails["realWorldTargeting"] is False
    assert guardrails["autonomousTargeting"] is False
    assert guardrails["rfInterference"] is False
    assert guardrails["deauthenticationExecution"] is False
    assert guardrails["exploitExecution"] is False
    assert guardrails["commandInjectionExecution"] is False
    assert guardrails["firmwareModificationExecution"] is False
    assert guardrails["dataExfiltrationExecution"] is False


def test_source_scenario_categories_are_preserved():
    data = _load()
    scenario_ids = {
        obj["id"] for obj in data["objects"] if obj["type"] == "ScenarioCategory"
    }
    assert scenario_ids == {
        "reconnaissance",
        "protocol-tampering",
        "denial-of-service",
        "injection",
        "exfiltration",
        "firmware-attacks",
    }


def test_actions_are_local_simulation_only():
    for action in _load()["actions"]:
        assert action["externalMutation"] is False
        assert action["simulationOnly"] is True
        assert action["requiresAuthorizedScope"] is True
