import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO_ID = "uijZR7hnDGM"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


def test_shared_source_is_candidate_only() -> None:
    record = json.loads(
        (ROOT / "intel" / "sources" / f"youtube-{VIDEO_ID}.json").read_text()
    )
    assert record["url"] == VIDEO_URL
    assert record["target_agents"] == ["GPT-DOUG-LLM", "GPT-REDPANDA-LLM"]
    assert record["learning_state"]["status"] == "CANDIDATE"
    assert record["learning_state"]["confidence"] == 0.0
    assert record["learning_state"]["claim_count"] == 0
    assert record["learning_state"]["promotion_allowed"] is False
    assert record["controls"]["invent_missing_claims"] is False
    assert record["controls"]["auto_promote"] is False


def test_redpanda_binding_matches_shared_source() -> None:
    binding = json.loads(
        (
            ROOT
            / "gpt-redpanda-llm"
            / "intel"
            / "sources"
            / f"youtube-{VIDEO_ID}.json"
        ).read_text()
    )
    assert binding["agent"] == "GPT-REDPANDA-LLM"
    assert binding["source_url"] == VIDEO_URL
    assert binding["ingestion_state"] == "CANDIDATE"
    assert binding["confidence"] == 0.0
    assert binding["claim_count"] == 0
    assert binding["verification"]["transcript_available"] is False
    assert binding["verification"]["promotion_allowed"] is False


def test_ontologi_registers_source_without_evidence_link() -> None:
    program = (ROOT / "va3lm" / "knowledge" / "core.ontologi").read_text()
    seed_id = f"source:video_{VIDEO_ID}"
    expected = (
        f'SEED {seed_id} Source "{VIDEO_URL}" '
        "status=CANDIDATE confidence=0.0"
    )
    assert expected in program
    assert f"LINK {seed_id} EVIDENCES" not in program
