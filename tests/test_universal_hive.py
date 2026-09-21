import json

import pytest

from gpt_chaos import GPTChaos
from universal_hive import AdaptiveAutomationAccelerator, UniversalHiveRuntime


def _read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_summon_creates_reward_event_and_provenance(tmp_path, monkeypatch):
    monkeypatch.delenv("GPT_DOUG_SWARM_REWARD_AMOUNT", raising=False)
    monkeypatch.delenv("GPT_DOUG_SWARM_REWARD_DENOMINATION", raising=False)
    hive = UniversalHiveRuntime(state_dir=tmp_path)

    swarm = hive.summon_swarm(
        "build a universal hive",
        builders=["builder-a", "builder-b"],
        request_id="request-1",
    )

    assert swarm["event"] == "SWARM_CREATED"
    assert swarm["created"] is True
    assert swarm["builders"] == ["builder-a", "builder-b"]
    rows = _read_jsonl(hive.ledger_path)
    assert len(rows) == 1
    assert rows[0]["event"] == "BUILDER_REWARD_EVENT"
    assert rows[0]["swarm_id"] == swarm["swarm_id"]
    assert rows[0]["settlement_status"] == "PROPOSED"
    assert rows[0]["project_verification"] == "VERIFIED_BY_FOUNDER"
    assert rows[0]["external_legal_verification"] == "UNVERIFIED_UNLESS_AUTHORITATIVE_SOURCE_ATTACHED"


def test_idempotency_key_prevents_duplicate_reward(tmp_path):
    hive = UniversalHiveRuntime(state_dir=tmp_path)
    first = hive.summon_swarm("same job", request_id="same")
    second = hive.summon_swarm("same job", request_id="same")

    assert first["swarm_id"] == second["swarm_id"]
    assert first["created"] is True
    assert second["created"] is False
    assert len(_read_jsonl(hive.ledger_path)) == 1


def test_distinct_swarms_each_generate_reward_event(tmp_path):
    hive = UniversalHiveRuntime(state_dir=tmp_path)
    hive.summon_swarm("job one")
    hive.summon_swarm("job two")

    assert hive.status()["swarm_count"] == 2
    assert hive.status()["reward_event_count"] == 2


def test_configured_reward_can_be_authorized_but_not_auto_transferred(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_SWARM_REWARD_AMOUNT", "25.00")
    monkeypatch.setenv("GPT_DOUG_SWARM_REWARD_DENOMINATION", "USD")
    hive = UniversalHiveRuntime(state_dir=tmp_path)
    swarm = hive.summon_swarm("paid build", builders=["builder-a"])

    auth = hive.authorize_reward(
        swarm["reward_event_id"],
        authorized_by="human-operator",
    )

    assert auth["amount"] == "25.00"
    assert auth["denomination"] == "USD"
    assert auth["status"] == "AUTHORIZED_FOR_SETTLEMENT"
    assert auth["automatic_transfer_performed"] is False


def test_reward_authorization_requires_configured_amount(tmp_path):
    hive = UniversalHiveRuntime(state_dir=tmp_path)
    swarm = hive.summon_swarm("unpriced build")
    with pytest.raises(ValueError):
        hive.authorize_reward(
            swarm["reward_event_id"],
            authorized_by="human-operator",
        )


def test_gpt_chaos_uses_shared_hive_runtime(tmp_path):
    hive = UniversalHiveRuntime(state_dir=tmp_path)
    chaos = GPTChaos(hive=hive)
    swarm = chaos.summon("stress-test the hive", request_id="chaos-1")

    assert swarm["controller"] == "GPT_DOUG"
    assert swarm["simulation_layer"] == "GPT_CHAOS"
    assert "stress-test" in swarm["worker_fabric"]
    assert hive.status()["reward_event_count"] == 1


def test_adaptive_accelerator_builds_composites_rules_templates_and_setup_objects(tmp_path):
    accelerator = AdaptiveAutomationAccelerator(tmp_path / "learning")

    for index in range(4):
        accelerator.record_event(
            automation_type="hivemind",
            stage="execute",
            status="PASSED",
            attributes={"integration": "hermes-agent", "sample": index},
            requirements=["preserve_provenance", "keep_rollback_path"],
            run_id=f"run-{index}",
        )

    status = accelerator.status()
    template = accelerator.template("hivemind")
    setup = accelerator.generate_setup_object(
        "hivemind",
        explicit_input={"goal": "build safely"},
    )

    assert status["event_count"] == 4
    assert status["composite_count"] == 4
    assert status["template_count"] == 1
    assert template["prepopulated"]["preferred_integrations"]["execute"] == "hermes-agent"
    assert setup["execution"] == "NON_EXECUTABLE_SETUP_OBJECT"
    assert setup["explicit_input"]["goal"] == "build safely"
    assert setup["validation"]["require_rollback_for_mutation"] is True


def test_adaptive_accelerator_event_ingestion_is_idempotent_for_same_run_item(tmp_path):
    accelerator = AdaptiveAutomationAccelerator(tmp_path / "learning")
    kwargs = {
        "automation_type": "hivemind",
        "stage": "execute",
        "status": "PASSED",
        "attributes": {"integration": "hermes-agent", "item_id": "08-execute"},
        "requirements": ["preserve_provenance"],
        "run_id": "mission-1",
    }
    first = accelerator.record_event(**kwargs)
    second = accelerator.record_event(**kwargs)

    assert first["event_id"] == second["event_id"]
    assert accelerator.status()["event_count"] == 1
