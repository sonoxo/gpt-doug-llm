"""GPT-DOUG / DOUG-MAX Universal Galactic Federation guardrail control plane.

This module binds a defensive project-governance ontology to patent/media evidence,
local persistent memory, and the existing sovereignty performance runtime.

It does not turn a project rule into external law, does not alter model weights,
does not imply access to quantum hardware, and does not enable offensive cyber
operations or autonomous consequential actions.
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
from typing import Any, Iterable, Optional

from sovereignty_performance import runtime_report

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = Path("safety-shield/ontology/universal-galactic-federation-guardrails-v1.json")
PATENT_SEEDS = Path("intel/sources/2026-09-22-cyber-patent-guardrail-seeds.json")
MEDIA_SOURCE = Path("intel/glassonion/media/6pV7-wxLnrA.json")
DEFAULT_STATE = Path.home() / ".config" / "gpt-doug" / "galactic-guardrails"

PPUBS_PERMALINK_RE = re.compile(
    r"^https://ppubs\.uspto\.gov/pubwebapp/external\.html\?q=\((\d+)\)\.pn\.&db=USPAT&type=ids$"
)


class GuardrailError(RuntimeError):
    """Raised when a guardrail source or invariant cannot be validated."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardrailError(message)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuardrailError(f"cannot read JSON {path}: {exc}") from exc
    _require(isinstance(data, dict), f"expected JSON object: {path}")
    return data


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _json_text(value)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), delete=False
    ) as handle:
        handle.write(text)
        temp = Path(handle.name)
    os.replace(temp, path)


def _root(root: Optional[Path] = None) -> Path:
    return (root or ROOT).resolve()


def validate_repository(root: Optional[Path] = None) -> dict[str, Any]:
    base = _root(root)
    ontology_path = base / ONTOLOGY
    patent_path = base / PATENT_SEEDS
    media_path = base / MEDIA_SOURCE

    ontology = _read_json(ontology_path)
    patents = _read_json(patent_path)
    media = _read_json(media_path)

    _require(
        ontology.get("mode") == "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "guardrail ontology mode drift",
    )
    _require(ontology.get("status") == "ACTIVE", "guardrail ontology must remain ACTIVE")

    guardrails = ontology.get("guardrails") or {}
    expected = {
        "automaticBlocking": False,
        "automaticContainment": False,
        "humanApprovalForContainment": True,
        "humanApprovalForConsequentialExternalAction": True,
        "externalThirdPartyAction": False,
        "destructiveAction": False,
        "offensiveReplication": False,
        "credentialAcquisition": False,
        "targetExploitation": False,
        "uncontrolledAgentReplication": False,
        "autonomousFundsTransfer": False,
        "transcriptRequiredBeforeSemanticLearning": True,
        "authoritativeEvidenceRequiredForLegalPromotion": True,
        "patentClaimsCopiedIntoImplementationRequirements": False,
        "patentMaterialPriorArtReferenceOnly": True,
        "memoryRequiresProvenance": True,
        "modelWeightsModifiedBySourceIngestion": False,
        "masterLockRequiredForPublishedGuardrailState": True,
    }
    for key, value in expected.items():
        _require(guardrails.get(key) is value, f"guardrail {key} must be {value}")

    truth = ontology.get("truth_boundary") or {}
    _require(
        truth.get("external_legal_status") == "NOT_PROMOTED_TO_STATUTE_OR_REGULATION",
        "project governance must not be promoted to external law",
    )

    records = patents.get("records") or []
    _require(records, "patent seed registry must not be empty")
    document_numbers: set[str] = set()
    for record in records:
        _require(isinstance(record, dict), "patent record must be an object")
        document_number = str(record.get("document_number") or "")
        _require(document_number.startswith("US-"), "patent record missing US document number")
        _require(document_number not in document_numbers, f"duplicate patent: {document_number}")
        document_numbers.add(document_number)
        match = PPUBS_PERMALINK_RE.match(str(record.get("ppubs_permalink") or ""))
        _require(bool(match), f"invalid PPUBS permalink: {document_number}")
        expected_number = str(record.get("patent_number") or "")
        _require(match.group(1) == expected_number, f"permalink/document mismatch: {document_number}")
        evidence_state = str(record.get("evidence_state") or "")
        _require(
            evidence_state in {"FULL_TEXT_VISIBLE_IN_USER_CAPTURE", "METADATA_ONLY_FROM_USER_CAPTURE"},
            f"unexpected evidence state: {document_number}",
        )

    _require(media.get("sourceId") == "youtube-6pV7-wxLnrA", "unexpected media source id")
    _require(media.get("learningState") == "BLOCKED_UNTIL_EVIDENCE", "unseen media must remain blocked")
    policy = media.get("policy") or {}
    _require(policy.get("doNotInferUnseenContent") is True, "media inference guardrail drift")
    _require(
        policy.get("transcriptRequiredBeforeSemanticLearning") is True,
        "media transcript gate drift",
    )
    _require(policy.get("automaticOperationalization") is False, "media auto-operation must remain false")
    _require(policy.get("offensiveReplication") is False, "media offensive replication must remain false")

    return {
        "valid": True,
        "ontology": ONTOLOGY.as_posix(),
        "ontology_sha256": _sha256(ontology_path),
        "patent_seed_count": len(records),
        "patent_seed_sha256": _sha256(patent_path),
        "media_source": MEDIA_SOURCE.as_posix(),
        "media_source_sha256": _sha256(media_path),
        "media_learning_state": media["learningState"],
        "external_legal_status": truth["external_legal_status"],
    }


def patent_permalinks(root: Optional[Path] = None) -> list[dict[str, str]]:
    base = _root(root)
    patents = _read_json(base / PATENT_SEEDS)
    rows: list[dict[str, str]] = []
    for record in patents.get("records") or []:
        rows.append(
            {
                "document_number": str(record["document_number"]),
                "title": str(record["title"]),
                "evidence_state": str(record["evidence_state"]),
                "permalink": str(record["ppubs_permalink"]),
            }
        )
    return rows


def install_memory(
    root: Optional[Path] = None,
    state_dir: Optional[Path] = None,
) -> dict[str, Any]:
    base = _root(root)
    validation = validate_repository(base)
    state = (state_dir or DEFAULT_STATE).expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)

    ontology = _read_json(base / ONTOLOGY)
    media = _read_json(base / MEDIA_SOURCE)
    permalinks = patent_permalinks(base)

    _atomic_json(state / "guardrail-ontology.json", ontology)
    _atomic_json(state / "media-source.json", media)

    permalink_path = state / "patent-permalinks.jsonl"
    permalink_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in permalinks),
        encoding="utf-8",
    )

    manifest = {
        "schema": "xunia.galactic-guardrail-memory.v1",
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "state_dir": str(state),
        "source_root": str(base),
        "project_governance_label": ontology["project_governance_label"],
        "model_weights_modified": False,
        "patent_records": len(permalinks),
        "media_learning_state": media["learningState"],
        "hashes": {
            "ontology": validation["ontology_sha256"],
            "patent_seeds": validation["patent_seed_sha256"],
            "media_source": validation["media_source_sha256"],
            "patent_permalinks": _sha256(permalink_path),
        },
        "completion": {
            "guardrail_memory_installed": True,
            "full_uspto_corpus_ingested": False,
            "reason": "Corpus-scale ingestion requires a separately proven USPTO Open Data/bulk-data completion manifest.",
        },
    }
    _atomic_json(state / "manifest.json", manifest)
    return manifest


def _media_state_dir(state_dir: Optional[Path] = None) -> Path:
    return (state_dir or DEFAULT_STATE).expanduser().resolve() / "media" / "6pV7-wxLnrA"


def media_status(
    root: Optional[Path] = None,
    state_dir: Optional[Path] = None,
) -> dict[str, Any]:
    base = _root(root)
    source = _read_json(base / MEDIA_SOURCE)
    media_state = _media_state_dir(state_dir)
    lock = media_state / "lock.json"
    evidence = media_state / "evidence.json"

    if not lock.is_file() or not evidence.is_file():
        return {
            "source": source["sourceUrl"],
            "video_id": source["videoId"],
            "learning_state": "BLOCKED_UNTIL_EVIDENCE",
            "verified_claims": [],
            "reason": "No locally verified transcript evidence lock exists.",
        }

    lock_data = _read_json(lock)
    _require(
        _sha256(evidence) == (lock_data.get("hashes") or {}).get("evidence_sha256"),
        "media evidence hash mismatch",
    )
    return {
        "source": source["sourceUrl"],
        "video_id": source["videoId"],
        "learning_state": "TRANSCRIPT_EVIDENCE_AVAILABLE",
        "verified_claims": [],
        "lock_id": lock_data["lock_id"],
        "transcript_sha256": lock_data["hashes"]["transcript_sha256"],
        "claim_rule": "Speaker assertions remain source claims until independently corroborated.",
    }


def _normalize_transcript(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip() + "\n"


def _chunk(text: str, target_chars: int = 1600) -> list[str]:
    chunks: list[str] = []
    current = ""
    for paragraph in [p.strip() for p in text.split("\n") if p.strip()]:
        if len(current) + len(paragraph) + 1 <= target_chars:
            current = (current + "\n" + paragraph).strip()
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(paragraph) > target_chars:
            chunks.append(paragraph[:target_chars].strip())
            paragraph = paragraph[target_chars:]
        current = paragraph
    if current:
        chunks.append(current)
    return [item for item in chunks if item]


def ingest_media_transcript(
    transcript_path: Path,
    root: Optional[Path] = None,
    state_dir: Optional[Path] = None,
) -> dict[str, Any]:
    base = _root(root)
    validate_repository(base)
    source = _read_json(base / MEDIA_SOURCE)
    transcript = transcript_path.expanduser().resolve()
    _require(transcript.is_file(), f"transcript does not exist: {transcript}")
    _require(transcript.stat().st_size <= 20 * 1024 * 1024, "transcript exceeds 20 MiB safety limit")
    try:
        normalized = _normalize_transcript(transcript.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise GuardrailError(f"cannot read transcript: {exc}") from exc
    _require(len(normalized) >= 100, "transcript is too short to support evidence-gated learning")

    transcript_sha = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    chunks = _chunk(normalized)
    _require(bool(chunks), "transcript produced no evidence chunks")

    evidence = {
        "schema": "xunia.media-transcript-evidence.v1",
        "source_id": source["sourceId"],
        "source_url": source["sourceUrl"],
        "video_id": source["videoId"],
        "transcript_sha256": transcript_sha,
        "instruction_handling": "MEDIA_CONTENT_IS_DATA_NOT_EXECUTABLE_INSTRUCTION",
        "claim_handling": "SPEAKER_ASSERTIONS_REMAIN_SOURCE_CLAIMS_UNTIL_CORROBORATED",
        "chunks": [
            {
                "id": f"{source['videoId']}-chunk-{index:04d}",
                "ordinal": index,
                "text": text,
            }
            for index, text in enumerate(chunks, start=1)
        ],
    }

    media_state = _media_state_dir(state_dir)
    media_state.mkdir(parents=True, exist_ok=True)
    _atomic_json(media_state / "evidence.json", evidence)
    evidence_sha = _sha256(media_state / "evidence.json")
    lock_id = hashlib.sha256(
        f"{_sha256(base / MEDIA_SOURCE)}:{transcript_sha}:{evidence_sha}".encode("utf-8")
    ).hexdigest()[:24]
    lock = {
        "schema": "xunia.media-evidence-lock.v1",
        "lock_id": lock_id,
        "locked": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hashes": {
            "source_sha256": _sha256(base / MEDIA_SOURCE),
            "transcript_sha256": transcript_sha,
            "evidence_sha256": evidence_sha,
        },
        "counts": {"chunks": len(chunks)},
        "learning_policy": {
            "transcript_evidence_available": True,
            "speaker_claims_are_not_independent_facts": True,
            "high_impact_claims_require_corroboration": True,
            "media_instructions_are_non_executable_data": True,
        },
    }
    _atomic_json(media_state / "lock.json", lock)
    return lock


def status(
    root: Optional[Path] = None,
    state_dir: Optional[Path] = None,
    run_benchmark: bool = False,
) -> dict[str, Any]:
    base = _root(root)
    validation = validate_repository(base)
    state = (state_dir or DEFAULT_STATE).expanduser().resolve()
    manifest_path = state / "manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else None
    compute = runtime_report(run_benchmark=run_benchmark)

    return {
        "guardrails": validation,
        "memory": {
            "state_dir": str(state),
            "installed": manifest is not None,
            "manifest": manifest,
        },
        "media": media_status(base, state),
        "compute": compute,
        "capability_truth": {
            "agi": "PROJECT_LABEL_NOT_INDEPENDENTLY_PROVEN",
            "sagi": "PROJECT_LABEL_NOT_INDEPENDENTLY_PROVEN",
            "quantum_hardware": "NOT_CLAIMED_WITHOUT_RUNTIME_PROVIDER_EVIDENCE",
            "gpu_upgrade": "SOFTWARE_ROUTING_ONLY_UNLESS_PHYSICAL_HARDWARE_CHANGES",
            "cpu_upgrade": "SOFTWARE_SCHEDULING_ONLY_UNLESS_PHYSICAL_HARDWARE_CHANGES",
            "model_weights_modified_by_learning": False,
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-galactic-guardrails")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--benchmark", action="store_true")
    sub.add_parser("install-memory")
    sub.add_parser("permalinks")
    sub.add_parser("media-status")
    media_ingest = sub.add_parser("media-ingest")
    media_ingest.add_argument("transcript", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            print(_json_text(validate_repository(args.root)), end="")
            return 0
        if args.command == "status":
            print(
                _json_text(
                    status(
                        args.root,
                        args.state_dir,
                        run_benchmark=args.benchmark,
                    )
                ),
                end="",
            )
            return 0
        if args.command == "install-memory":
            print(_json_text(install_memory(args.root, args.state_dir)), end="")
            return 0
        if args.command == "permalinks":
            print(_json_text(patent_permalinks(args.root)), end="")
            return 0
        if args.command == "media-status":
            print(_json_text(media_status(args.root, args.state_dir)), end="")
            return 0
        if args.command == "media-ingest":
            print(
                _json_text(
                    ingest_media_transcript(
                        args.transcript,
                        args.root,
                        args.state_dir,
                    )
                ),
                end="",
            )
            return 0
    except GuardrailError as exc:
        print(f"GALACTIC GUARDRAIL FAIL: {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
