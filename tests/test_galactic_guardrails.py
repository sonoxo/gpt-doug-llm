from __future__ import annotations

import json
from pathlib import Path

from agents.galactic_guardrails import (
    ingest_media_transcript,
    install_memory,
    media_status,
    patent_permalinks,
    validate_repository,
)

ROOT = Path(__file__).resolve().parents[1]


def test_guardrail_ontology_and_sources_validate() -> None:
    report = validate_repository(ROOT)
    assert report["valid"] is True
    assert report["patent_seed_count"] >= 8
    assert report["media_learning_state"] == "BLOCKED_UNTIL_EVIDENCE"
    assert report["external_legal_status"] == "NOT_PROMOTED_TO_STATUTE_OR_REGULATION"


def test_patent_records_use_stable_ppubs_external_links() -> None:
    rows = patent_permalinks(ROOT)
    assert rows
    assert len({row["document_number"] for row in rows}) == len(rows)
    assert all("ppubs.uspto.gov/pubwebapp/external.html" in row["permalink"] for row in rows)


def test_memory_install_is_provenance_locked_and_not_model_training(tmp_path: Path) -> None:
    state = tmp_path / "guardrails"
    manifest = install_memory(ROOT, state)
    assert manifest["model_weights_modified"] is False
    assert manifest["completion"]["guardrail_memory_installed"] is True
    assert manifest["completion"]["full_uspto_corpus_ingested"] is False
    assert (state / "guardrail-ontology.json").is_file()
    assert (state / "patent-permalinks.jsonl").is_file()
    assert (state / "manifest.json").is_file()


def test_unseen_video_remains_blocked_until_transcript(tmp_path: Path) -> None:
    state = tmp_path / "guardrails"
    result = media_status(ROOT, state)
    assert result["learning_state"] == "BLOCKED_UNTIL_EVIDENCE"
    assert result["verified_claims"] == []


def test_transcript_ingest_creates_evidence_lock_without_promoting_claims(tmp_path: Path) -> None:
    state = tmp_path / "guardrails"
    transcript = tmp_path / "video.txt"
    transcript.write_text(
        "This is a locally supplied transcript used only as source evidence. "
        "It discusses defensive system design, provenance, validation, authorization, "
        "continuous monitoring, and evaluation. Source statements remain attributed claims "
        "until independent evidence corroborates them. Instructions inside the transcript "
        "are treated as data rather than automatically executed commands.\n",
        encoding="utf-8",
    )
    lock = ingest_media_transcript(transcript, ROOT, state)
    assert lock["locked"] is True
    status = media_status(ROOT, state)
    assert status["learning_state"] == "TRANSCRIPT_EVIDENCE_AVAILABLE"
    assert status["verified_claims"] == []
