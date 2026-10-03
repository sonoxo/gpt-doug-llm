from __future__ import annotations

from datetime import UTC, datetime, timedelta

from va3lm.memory_garden import MemoryGarden
from va3lm.ontologi import Link, OntologiEngine, Program, Seed


def test_memory_garden_observe_and_snapshot_round_trip():
    engine = OntologiEngine.load_default()
    garden = MemoryGarden(engine)
    now = datetime(2026, 9, 7, tzinfo=UTC)
    garden.observe(["agent:virginia", "concept:ontologi"], now=now)

    restored = MemoryGarden.from_snapshot(engine, garden.snapshot())
    assert restored.active_seed_ids() == ["agent:virginia", "concept:ontologi"]
    assert restored.records["agent:virginia"].first_seen == now.isoformat()


def test_candidate_reinforcement_never_self_promotes():
    engine = OntologiEngine.load_default()
    candidate = engine.stage_seed("claim:garden:test", "Claim", "Observed knowledge remains candidate until evidence promotion.")
    garden = MemoryGarden(engine)
    strengthened = garden.reinforce(candidate.id, amount=0.25, now=datetime(2026, 9, 7, tzinfo=UTC))
    strengthened = garden.reinforce(candidate.id, amount=0.25, now=datetime(2026, 9, 8, tzinfo=UTC))
    strengthened = garden.reinforce(candidate.id, amount=0.25, now=datetime(2026, 9, 9, tzinfo=UTC))

    assert strengthened.status == "CANDIDATE"
    assert strengthened.confidence == 0.69
    assert garden.records[candidate.id].reinforcements == 3


def test_age_marks_stale_and_archived_candidates_without_deleting_them():
    engine = OntologiEngine.load_default()
    stale_seed = engine.stage_seed("claim:garden:stale", "Claim", "This candidate should become stale after enough quiet time.")
    archived_seed = engine.stage_seed("claim:garden:archive", "Claim", "This candidate should become archived after a longer quiet period.")
    garden = MemoryGarden(engine)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    garden.observe([stale_seed.id], now=base + timedelta(days=40))
    garden.observe([archived_seed.id], now=base)

    result = garden.age(now=base + timedelta(days=100), candidate_stale_days=30, candidate_archive_days=90)
    assert stale_seed.id in result["staleSeedIds"]
    assert archived_seed.id in result["archivedSeedIds"]
    assert {seed.id for seed in engine.program.seeds} >= {stale_seed.id, archived_seed.id}


def test_verified_confidence_decay_has_trust_floor():
    engine = OntologiEngine.load_default()
    garden = MemoryGarden(engine)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    garden.observe(["concept:ontologi"], now=base)
    garden.age(now=base + timedelta(days=500), verified_decay_per_day=0.01)

    seed = next(seed for seed in engine.program.seeds if seed.id == "concept:ontologi")
    assert seed.status == "VERIFIED"
    assert seed.confidence == 0.7


def test_contradictions_require_review_and_ignore_rejected_side():
    engine = OntologiEngine.load_default()
    left = Seed("claim:left", "Claim", "The system should use path A.", status="VERIFIED", confidence=0.9)
    right = Seed("claim:right", "Claim", "The system should not use path A.", status="CANDIDATE", confidence=0.4)
    engine.program = Program(
        engine.program.version,
        engine.program.seeds + (left, right),
        engine.program.links + (Link(left.id, "CONTRADICTS", right.id),),
    )
    garden = MemoryGarden(engine)

    conflicts = garden.contradictions()
    assert conflicts == [
        {
            "left": "claim:left",
            "leftStatus": "VERIFIED",
            "leftConfidence": 0.9,
            "right": "claim:right",
            "rightStatus": "CANDIDATE",
            "rightConfidence": 0.4,
            "resolution": "REVIEW_REQUIRED",
        }
    ]
