from __future__ import annotations

import pytest
from va3lm.ontologi import CORE_ONTOLOGI, OntologiEngine, OntologiError, parse


def test_core_ontologi_seed_program_is_valid():
    program = parse(CORE_ONTOLOGI)
    assert program.version == "1.0"
    assert len(program.seeds) == 10
    assert len(program.links) == 7


def test_video_reference_stays_candidate_until_verified():
    engine = OntologiEngine.load_default()
    graph = {seed.id: seed for seed in engine.program.seeds}
    video = graph["source:video_wzgkc6Iegx8"]
    assert video.status == "CANDIDATE"
    assert video.confidence == 0.0


def test_seed_retrieval_prefers_relevant_verified_knowledge():
    engine = OntologiEngine.load_default()
    results = engine.retrieve("ontology seed language learning", limit=4)
    assert results
    assert results[0]["status"] == "VERIFIED"
    assert "concept:ontologi" in {item["id"] for item in results}


def test_learning_is_candidate_first_and_evidence_gated():
    engine = OntologiEngine.load_default()
    staged = engine.stage_seed("concept:new_learning", "Concept", "A newly observed idea", tags=["learning"])
    assert staged.status == "CANDIDATE"
    with pytest.raises(OntologiError):
        engine.promote_seed("concept:new_learning", confidence=0.9, evidence_ids=[])
    promoted = engine.promote_seed("concept:new_learning", confidence=0.9, evidence_ids=["evidence:test"])
    assert promoted.status == "VERIFIED"
    assert promoted.confidence == 0.9
