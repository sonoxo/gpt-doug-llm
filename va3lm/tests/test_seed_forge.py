from __future__ import annotations

import pytest
from va3lm.ontologi import OntologiEngine, OntologiError
from va3lm.seed_forge import ForgeArtifact, SeedForge


def test_seed_forge_creates_candidate_claims_with_provenance():
    engine = OntologiEngine.load_default()
    forge = SeedForge(engine)
    result = forge.ingest(
        ForgeArtifact(
            path="docs/forge-demo.md",
            content="# Forge Demo\nVirginia uses governed ontology seeds for reasoning.\nEvidence controls promotion of learned knowledge.",
            verified_source=True,
            tags=("demo",),
        )
    )
    assert result["created"] == 2
    assert result["automaticPromotion"] is False
    claims = {seed.id: seed for seed in engine.program.seeds if seed.id in result["createdSeedIds"]}
    assert claims and all(seed.status == "CANDIDATE" for seed in claims.values())
    assert all(
        any(link.source == seed_id and link.relation == "DERIVED_FROM" and link.target == result["sourceId"] for link in engine.program.links)
        for seed_id in claims
    )


def test_seed_forge_deduplicates_repeat_ingest():
    engine = OntologiEngine.load_default()
    forge = SeedForge(engine)
    artifact = ForgeArtifact(
        path="docs/repeat.md",
        content="Structured evidence should remain attached to its provenance source.",
        verified_source=True,
    )
    first = forge.ingest(artifact)
    second = forge.ingest(artifact)
    assert first["created"] == 1
    assert second["created"] == 0
    assert second["duplicates"] == 1


def test_seed_forge_blocks_repository_escape():
    forge = SeedForge(OntologiEngine.load_default())
    with pytest.raises(OntologiError):
        forge.ingest(ForgeArtifact(path="../secret.txt", content="This must never be ingested from outside the repository."))


def test_seed_forge_promotion_requires_real_verified_evidence():
    engine = OntologiEngine.load_default()
    forge = SeedForge(engine)
    result = forge.ingest(
        ForgeArtifact(
            path="docs/evidence.md",
            content="A candidate seed can only become verified after evidence review.",
            verified_source=True,
        )
    )
    claim_id = result["createdSeedIds"][0]
    with pytest.raises(OntologiError):
        forge.promote(claim_id, confidence=0.9, evidence_ids=["evidence:missing"])
    promoted = forge.promote(claim_id, confidence=0.9, evidence_ids=[result["sourceId"]])
    assert promoted.status == "VERIFIED"
    assert promoted.confidence == 0.9


def test_seed_forge_extracts_python_docstrings_not_code_lines():
    forge = SeedForge(OntologiEngine.load_default())
    statements = forge.extract_statements(
        "va3lm/src/example.py",
        '"""Module knowledge explains the governed learning boundary."""\n\ndef run():\n    """Run only after policy validation completes."""\n    return True\n',
    )
    assert statements == [
        "Module knowledge explains the governed learning boundary.",
        "Run only after policy validation completes.",
    ]
