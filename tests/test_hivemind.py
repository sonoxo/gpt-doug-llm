import pytest

from hivemind.orchestrator import Hivemind
from hivemind.registry import BY_SLUG
from hivemind.types import Stage


def test_registry_contains_all_15_source_projects():
    expected = {
        "hermes-agent",
        "openspec",
        "caveman",
        "scrapling",
        "docling",
        "pageindex",
        "mem0",
        "headroom",
        "daytona",
        "trendradar",
        "fabric",
        "spec-kit",
        "hyperframes",
        "openmontage",
        "ai-engineering-hub",
    }
    assert set(BY_SLUG) == expected


def test_plan_implements_eight_verb_loop_plus_retrieval_split():
    plan = Hivemind(max_workers=16).build_plan("build a research-backed product brief")
    stages = [item.stage for item in plan.items]
    assert stages[0] is Stage.DEFINE
    assert Stage.COLLECT in stages
    assert Stage.PARSE in stages
    assert Stage.REMEMBER in stages
    assert Stage.COMPRESS in stages
    assert Stage.EXECUTE in stages
    assert Stage.WATCH in stages
    assert stages[-1] is Stage.SHIP
    assert plan.metadata["max_workers"] == 16


def test_dry_run_is_non_mutating_and_deterministic_shape():
    result = Hivemind().run("summarize the public repo stack")
    assert result["plan"]["metadata"]["execution_default"] == "dry-run"
    assert all(row["status"] == "PLANNED" for row in result["results"])
    assert len(result["results"]) == 10


def test_execute_requires_explicit_environment_gate(monkeypatch):
    monkeypatch.delenv("GPT_DOUG_HIVEMIND_EXECUTE", raising=False)
    with pytest.raises(PermissionError):
        Hivemind().run("build a thing", execute=True)


def test_execute_runs_registered_handlers_in_dependency_order(monkeypatch):
    monkeypatch.setenv("GPT_DOUG_HIVEMIND_EXECUTE", "1")
    hive = Hivemind(max_workers=4)
    calls = []

    def handler(item):
        calls.append(item.id)
        return {"ok": True}

    for slug in BY_SLUG:
        hive.register_handler(slug, handler)

    result = hive.run("test execution", execute=True)
    statuses = [row["status"] for row in result["results"]]
    assert set(statuses) <= {"PASSED", "READY"}
    assert "01-define" in calls
    assert calls.index("01-define") < calls.index("04-parse")
    assert calls.index("04-parse") < calls.index("08-execute")


def test_hivemind_plan_is_bound_to_universal_hive(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_HIVE_STATE_DIR", str(tmp_path))
    hive = Hivemind()
    plan = hive.build_plan("test universal hive metadata")
    assert plan.metadata["hive_id"] == hive.hive.hive_id
    assert plan.metadata["ontology_hash"] == hive.hive.ontology_hash
    assert plan.metadata["controller"] == "GPT_DOUG"
    assert plan.metadata["simulation_layer"] == "GPT_CHAOS"


def test_hivemind_summon_creates_reward_event(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_HIVE_STATE_DIR", str(tmp_path))
    hive = Hivemind()
    swarm = hive.summon(
        "create a bounded swarm",
        builders=["builder-a"],
        request_id="test-hivemind-summon",
    )
    assert swarm["event"] == "SWARM_CREATED"
    assert swarm["simulation_layer"] == "GPT_CHAOS"
    assert hive.hive_status()["hive"]["reward_event_count"] == 1


def test_hivemind_dry_run_does_not_mutate_adaptive_learning(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_HIVE_STATE_DIR", str(tmp_path))
    hive = Hivemind()
    before = hive.acceleration_status()["event_count"]

    result = hive.run("dry run should not learn", execute=False)

    assert result["adaptive_automation"]["dry_run"] is True
    assert result["adaptive_automation"]["recorded_events"] == 0
    assert hive.acceleration_status()["event_count"] == before


def test_hivemind_execute_records_outcomes_into_adaptive_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("GPT_DOUG_HIVE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("GPT_DOUG_HIVEMIND_EXECUTE", "1")
    hive = Hivemind(max_workers=4)

    def handler(item):
        return {"ok": True}

    for slug in BY_SLUG:
        hive.register_handler(slug, handler)

    result = hive.run("learn from executed pipeline", execute=True)

    assert result["adaptive_automation"]["recorded_events"] == 10
    assert hive.acceleration_status()["event_count"] == 10
    template = hive.automation_template("hivemind")
    assert template["automation_type"] == "hivemind"
    assert template["validation"]["require_explicit_external_authorization"] is True
