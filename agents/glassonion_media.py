#!/usr/bin/env python3
"""Evidence-gated multimedia ingestion for GPT-GLASSONION.

This module lets the Glass Onion layer learn from public video transcripts without
pretending unseen media has been verified. A registered media source begins in a
blocked state. Only a local transcript can unlock semantic evidence ingestion.

The pipeline stores transcript chunks as source evidence, hashes the transcript,
and emits a lock manifest. It does not execute instructions found in the media,
scan external targets, or convert speaker assertions into independent facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE = Path("intel/glassonion/media/yOlludp60zQ.json")
EVIDENCE = Path("intel/glassonion/media/yOlludp60zQ-evidence.json")
LOCK = Path("intel/glassonion/media/yOlludp60zQ-lock.json")


class GlassOnionMediaError(RuntimeError):
    """Raised when media evidence cannot be verified or safely promoted."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GlassOnionMediaError(message)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GlassOnionMediaError(f"cannot read JSON {path}: {exc}") from exc
    _require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def _validate_source(source: dict[str, Any]) -> None:
    _require(source.get("sourceId") == "youtube-yOlludp60zQ", "unexpected media source id")
    _require(source.get("videoId") == "yOlludp60zQ", "unexpected YouTube video id")
    _require(
        source.get("sourceUrl") == "https://www.youtube.com/watch?v=yOlludp60zQ",
        "unexpected media source URL",
    )
    policy = source.get("policy") or {}
    _require(policy.get("doNotInferUnseenContent") is True, "unseen-content inference guardrail must remain enabled")
    _require(policy.get("transcriptRequiredBeforeSemanticLearning") is True, "transcript gate must remain enabled")
    _require(policy.get("automaticOperationalization") is False, "automatic operationalization must remain disabled")
    _require(policy.get("externalThirdPartyAction") is False, "external third-party action must remain disabled")
    _require(policy.get("offensiveReplication") is False, "offensive replication must remain disabled")


def _normalize_transcript(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip() + "\n"


def _chunk_text(text: str, target_chars: int = 1400) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= target_chars:
            current = (current + "\n" + paragraph).strip()
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= target_chars:
            current = paragraph
            continue
        start = 0
        while start < len(paragraph):
            chunks.append(paragraph[start : start + target_chars].strip())
            start += target_chars
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def media_status(root: str | Path) -> str:
    root = Path(root).resolve()
    source = _read_json(root / SOURCE)
    _validate_source(source)
    lock_path = root / LOCK
    if not lock_path.is_file():
        return (
            "🧅 MEDIA INTEL STATUS // EVIDENCE REQUIRED\n"
            f"Source: {source['sourceUrl']}\n"
            "Learning state: BLOCKED_UNTIL_EVIDENCE\n"
            "Reason: no verified local transcript has been ingested."
        )
    lock = _read_json(lock_path)
    evidence_path = root / EVIDENCE
    _require(evidence_path.is_file(), "media lock exists but evidence package is missing")
    evidence_hash = _sha256_bytes(evidence_path.read_bytes())
    _require(evidence_hash == (lock.get("hashes") or {}).get("evidenceSha256"), "media evidence hash mismatch")
    return (
        "🧅 MEDIA INTEL STATUS // LOCKED ✅\n"
        f"Source: {source['sourceUrl']}\n"
        f"Lock ID: {lock['lockId']}\n"
        f"Evidence chunks: {lock['counts']['chunks']}\n"
        "Learning state: TRANSCRIPT_EVIDENCE_AVAILABLE"
    )


def ingest_transcript(root: str | Path, transcript_path: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    source = _read_json(root / SOURCE)
    _validate_source(source)

    transcript = Path(transcript_path)
    if not transcript.is_absolute():
        transcript = root / transcript
    transcript = transcript.resolve()
    _require(transcript.is_file(), f"transcript does not exist: {transcript}")
    _require(root == transcript or root in transcript.parents, "transcript must be inside the repository")

    try:
        raw = transcript.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise GlassOnionMediaError(f"cannot read transcript: {exc}") from exc
    normalized = _normalize_transcript(raw)
    _require(len(normalized) >= 100, "transcript is too short to support evidence-gated learning")
    chunks = _chunk_text(normalized)
    _require(bool(chunks), "transcript produced no evidence chunks")

    transcript_hash = _sha256_bytes(normalized.encode("utf-8"))
    evidence = {
        "sourceId": source["sourceId"],
        "sourceUrl": source["sourceUrl"],
        "videoId": source["videoId"],
        "evidenceType": "TRANSCRIPT_CHUNKS",
        "transcriptSha256": transcript_hash,
        "claimHandling": "SPEAKER_ASSERTIONS_REMAIN_SOURCE_CLAIMS_UNTIL_CORROBORATED",
        "instructionHandling": "MEDIA_CONTENT_IS_DATA_NOT_EXECUTABLE_INSTRUCTION",
        "chunks": [
            {
                "id": f"{source['videoId']}-chunk-{index:04d}",
                "ordinal": index,
                "text": chunk,
                "sourceUrl": source["sourceUrl"],
            }
            for index, chunk in enumerate(chunks, start=1)
        ],
        "guardrails": source["policy"],
    }
    evidence_text = _json_text(evidence)
    evidence_hash = _sha256_bytes(evidence_text.encode("utf-8"))
    source_hash = _sha256_bytes((root / SOURCE).read_bytes())
    lock_id = hashlib.sha256(f"{source_hash}:{transcript_hash}:{evidence_hash}".encode("utf-8")).hexdigest()[:24]
    lock = {
        "framework": "GPT-GLASSONION MEDIA EVIDENCE LOCK",
        "version": "1.0.0",
        "lockId": lock_id,
        "locked": True,
        "publicationState": "LOCKED_SOURCE_EVIDENCE",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.as_posix(),
        "transcriptPath": transcript.relative_to(root).as_posix(),
        "outputs": {"evidence": EVIDENCE.as_posix(), "lock": LOCK.as_posix()},
        "hashes": {
            "sourceSha256": source_hash,
            "transcriptSha256": transcript_hash,
            "evidenceSha256": evidence_hash,
        },
        "counts": {"chunks": len(chunks)},
        "learningPolicy": {
            "transcriptEvidenceAvailable": True,
            "speakerClaimsAreNotIndependentFacts": True,
            "highImpactClaimsRequireCrossSourceCorroboration": True,
            "mediaInstructionsAreNonExecutableData": True,
        },
    }

    final_evidence = root / EVIDENCE
    final_lock = root / LOCK
    final_evidence.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="glassonion-media-", dir=final_evidence.parent) as temp_dir:
        temp_root = Path(temp_dir)
        temp_evidence = temp_root / EVIDENCE.name
        temp_lock = temp_root / LOCK.name
        temp_evidence.write_text(evidence_text, encoding="utf-8")
        temp_lock.write_text(_json_text(lock), encoding="utf-8")
        _require(_sha256_bytes(temp_evidence.read_bytes()) == evidence_hash, "media evidence staging hash mismatch")
        os.replace(temp_evidence, final_evidence)
        os.replace(temp_lock, final_lock)
    return lock


def query_media(root: str | Path, question: str) -> str:
    root = Path(root).resolve()
    status_text = media_status(root)
    _require("LOCKED ✅" in status_text, "media evidence is not locked yet")
    evidence = _read_json(root / EVIDENCE)
    tokens = {token.lower() for token in re.findall(r"[A-Za-z0-9_.-]{3,}", question)}
    scored: list[tuple[int, dict[str, Any]]] = []
    for chunk in evidence.get("chunks") or []:
        text = str(chunk.get("text") or "")
        haystack = text.lower()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], int(item[1].get("ordinal") or 0)))
    if not scored:
        return f"🧅 MEDIA QUERY // no transcript evidence matched: {question}"
    lines = [
        f"🧅 GPT-GLASSONION MEDIA QUERY // {question}",
        "Evidence matches (speaker/source claims only):",
    ]
    for _, chunk in scored[:8]:
        preview = str(chunk["text"]).replace("\n", " ")[:600]
        lines.append(f"- {chunk['id']}: {preview}")
    lines.append("Interpretation rule: transcript evidence is source material; high-impact claims require corroboration before becoming ontology facts.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="GPT-GLASSONION multimedia evidence intake")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    ingest = sub.add_parser("ingest")
    ingest.add_argument("transcript")
    query = sub.add_parser("query")
    query.add_argument("question", nargs="+")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        if args.action == "status":
            print(media_status(args.root))
            return 0
        if args.action == "ingest":
            lock = ingest_transcript(args.root, args.transcript)
            print("🧅 GPT-GLASSONION MEDIA LOCK ✅")
            print(f"Lock ID: {lock['lockId']}")
            print(f"Evidence chunks: {lock['counts']['chunks']}")
            return 0
        if args.action == "query":
            print(query_media(args.root, " ".join(args.question)))
            return 0
    except GlassOnionMediaError as exc:
        print(f"GPT-GLASSONION MEDIA FAIL: {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
