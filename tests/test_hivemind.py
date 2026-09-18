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
