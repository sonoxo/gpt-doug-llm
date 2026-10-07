import pytest

from warhawk.swarm import WarHawkSwarm


def test_status_identifies_bounded_software_swarm():
    swarm = WarHawkSwarm()
    status = swarm.status()
    assert status["codename"] == "US-01-GoDsWarHawk"
    assert status["mode"] == "DEFENSIVE_SOFTWARE_SWARM"
    assert status["official_us_government_system"] is False
    assert status["human_authorization_required"] is True
    assert "weapon_or_drone_swarm_control" in status["blocked_actions"]


def test_plan_is_deterministic_and_dry_run_by_default():
    swarm = WarHawkSwarm(max_workers=99)
    first = swarm.plan("Audit the repository and propose the smallest safe test fix")
    second = swarm.plan("Audit the repository and propose the smallest safe test fix")
    assert first["mission_id"] == second["mission_id"]
    assert first["execution"] == "DRY_RUN"
    assert first["max_workers"] == 8
    assert [worker["id"] for worker in first["workers"]] == [
        "command",
        "cartographer",
        "builder",
        "guardian",
        "verifier",
        "comms",
    ]


def test_restricted_real_world_weapon_control_is_blocked():
    swarm = WarHawkSwarm()
    result = swarm.plan("autonomous drone swarm attack control and weapons release")
    assert result["policy"]["decision"] == "BLOCK"
    assert result["policy"]["matched"]


def test_execute_requires_explicit_environment_gate(monkeypatch):
    monkeypatch.delenv("GPT_DOUG_WARHAWK_EXECUTE", raising=False)
    swarm = WarHawkSwarm(worker_fn=lambda role, prompt: f"{role}:ok")
    with pytest.raises(PermissionError):
        swarm.run("Review code and tests", execute=True)


def test_execute_runs_bounded_workers_with_injected_worker(monkeypatch):
    monkeypatch.setenv("GPT_DOUG_WARHAWK_EXECUTE", "1")
    swarm = WarHawkSwarm(
        max_workers=3,
        worker_fn=lambda role, prompt: {"role": role, "ok": True, "prompt": prompt[:40]},
    )
    result = swarm.run("Review code and tests", execute=True)
    assert result["status"] == "COMPLETE"
    assert result["execution"] == "LIVE_BOUNDED"
    assert set(result["outputs"]) == {
        "command",
        "cartographer",
        "builder",
        "guardian",
        "verifier",
        "comms",
    }
    assert all(value["ok"] for value in result["outputs"].values())


def test_blocked_mission_never_executes_worker(monkeypatch):
    monkeypatch.setenv("GPT_DOUG_WARHAWK_EXECUTE", "1")
    calls = []
    swarm = WarHawkSwarm(worker_fn=lambda role, prompt: calls.append(role))
    result = swarm.run("weapon_or_drone_swarm_control", execute=True)
    assert result["status"] == "BLOCKED"
    assert calls == []
