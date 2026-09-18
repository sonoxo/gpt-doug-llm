from __future__ import annotations

import time

from workers import revenue_swarm as rs


def fake_runner(stage, prompt, prospect, prior):
    return {
        "output": f"{stage}:{prospect.prospect_id}",
        "review_passed": True,
    }


def test_swarm_runs_full_pipeline_and_requires_outreach_approval(monkeypatch):
    monkeypatch.setattr(rs, "_provider_name", lambda: "remote")
    swarm = rs.RevenueSwarm(
        config=rs.SwarmConfig(requested_workers=8, hard_max_workers=16, persist=False),
        runner=fake_runner,
    )
    result = swarm.run(
        [
            rs.Prospect(
                prospect_id="p1",
                name="Alex",
                organization="Acme",
                channel="email",
            )
        ]
    )

    assert result["metrics"]["active_workers"] == 8
    assert result["metrics"]["pipelines_completed"] == 1
    assert result["metrics"]["stages_succeeded"] == len(rs.STAGES)
    assert result["metrics"]["stages_failed"] == 0
    assert result["metrics"]["awaiting_approval"] == 1
    assert result["pipelines"][0]["approval_required"] is True


def test_swarm_deduplicates_same_person_and_organization(monkeypatch):
    monkeypatch.setattr(rs, "_provider_name", lambda: "remote")
    swarm = rs.RevenueSwarm(
        config=rs.SwarmConfig(requested_workers=4, persist=False),
        runner=fake_runner,
    )
    result = swarm.run(
        [
            rs.Prospect("p1", name="Alex", organization="Acme", channel="email"),
            rs.Prospect("p2", name="alex", organization="ACME", channel="EMAIL"),
        ]
    )

    assert result["metrics"]["prospects_received"] == 2
    assert result["metrics"]["prospects_unique"] == 1
    assert result["metrics"]["prospects_deduped"] == 1


def test_ollama_provider_is_clamped_to_local_cap(monkeypatch):
    monkeypatch.setattr(rs, "_provider_name", lambda: "ollama")
    swarm = rs.RevenueSwarm(
        config=rs.SwarmConfig(
            requested_workers=64,
            hard_max_workers=64,
            local_provider_cap=2,
            persist=False,
        ),
        runner=fake_runner,
    )

    assert swarm.worker_count == 2


def test_parallelizes_independent_prospect_pipelines(monkeypatch):
    monkeypatch.setattr(rs, "_provider_name", lambda: "remote")

    def slow_runner(stage, prompt, prospect, prior):
        time.sleep(0.005)
        return {"output": stage, "review_passed": True}

    swarm = rs.RevenueSwarm(
        config=rs.SwarmConfig(requested_workers=4, hard_max_workers=4, persist=False),
        runner=slow_runner,
    )
    prospects = [
        rs.Prospect(f"p{i}", name=f"Person {i}", organization=f"Org {i}")
        for i in range(4)
    ]

    started = time.time()
    result = swarm.run(prospects)
    elapsed = time.time() - started

    assert result["metrics"]["pipelines_completed"] == 4
    # Four sequential pipelines would take about 0.12s from the artificial sleeps.
    # A four-worker pool should complete materially faster without relying on a
    # brittle exact timing threshold.
    assert elapsed < 0.11


def test_failed_stage_stops_only_that_pipeline(monkeypatch):
    monkeypatch.setattr(rs, "_provider_name", lambda: "remote")

    def mixed_runner(stage, prompt, prospect, prior):
        if prospect.prospect_id == "bad" and stage == "match":
            raise RuntimeError("synthetic failure")
        return {"output": stage, "review_passed": True}

    swarm = rs.RevenueSwarm(
        config=rs.SwarmConfig(requested_workers=2, persist=False),
        runner=mixed_runner,
    )
    result = swarm.run(
        [
            rs.Prospect("good", organization="Good Org"),
            rs.Prospect("bad", organization="Bad Org"),
        ]
    )

    assert result["metrics"]["pipelines_completed"] == 1
    assert result["metrics"]["stages_failed"] == 1
