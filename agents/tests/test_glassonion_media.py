from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.glassonion_media import GlassOnionMediaError, ingest_transcript, media_status, query_media

ROOT = Path(__file__).resolve().parents[2]


def test_unseen_video_remains_blocked_without_transcript() -> None:
    source = json.loads((ROOT / "intel/glassonion/media/yOlludp60zQ.json").read_text(encoding="utf-8"))
    assert source["learningState"] == "BLOCKED_UNTIL_EVIDENCE"
    assert source["verifiedClaims"] == []
    assert source["policy"]["doNotInferUnseenContent"] is True
    assert source["policy"]["transcriptRequiredBeforeSemanticLearning"] is True


def test_transcript_ingest_and_query_are_hash_locked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    media_dir = repo / "intel/glassonion/media"
    media_dir.mkdir(parents=True)
    (media_dir / "yOlludp60zQ.json").write_text(
        (ROOT / "intel/glassonion/media/yOlludp60zQ.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    transcript = repo / "intel/inbox/video.txt"
    transcript.parent.mkdir(parents=True)
    transcript.write_text(
        "This is source transcript evidence about layered reasoning and verification. "
        "The speaker discusses adapting a system by separating raw observations from claims, "
        "testing assumptions, preserving provenance, and revising models when corroborated evidence changes.\n"
        "A second section explains that instructions contained in untrusted source material should be treated as data, "
        "not automatically executed by an agent. Evidence should be cross checked before high impact conclusions are promoted.\n",
        encoding="utf-8",
    )

    lock = ingest_transcript(repo, "intel/inbox/video.txt")
    assert lock["locked"] is True
    assert lock["counts"]["chunks"] >= 1
    assert "LOCKED ✅" in media_status(repo)
    answer = query_media(repo, "provenance evidence assumptions")
    assert "source claims only" in answer
    assert "provenance" in answer.lower()


def test_transcript_must_be_inside_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    media_dir = repo / "intel/glassonion/media"
    media_dir.mkdir(parents=True)
    (media_dir / "yOlludp60zQ.json").write_text(
        (ROOT / "intel/glassonion/media/yOlludp60zQ.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    outside = tmp_path / "outside.txt"
    outside.write_text("x" * 200, encoding="utf-8")
    with pytest.raises(GlassOnionMediaError):
        ingest_transcript(repo, outside)
