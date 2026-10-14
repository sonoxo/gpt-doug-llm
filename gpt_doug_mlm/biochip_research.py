"""Bounded, offline-first multimodel and biochip *research* core.

No network, hardware, military, deployment, or self-modifying execution is performed.
Inputs are explicit, local, provenance-tagged research observations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
import json


@dataclass(frozen=True)
class Observation:
    source: str
    kind: str
    value: float
    unit: str
    timestamp: str
    consent_ref: str

    def validate(self) -> None:
        if self.kind not in {"neural_signal", "biochip_telemetry", "synthetic"}:
            raise ValueError("Unrecognized observation kind")
        if not self.source or not self.consent_ref or not self.unit:
            raise ValueError("Source, permission reference and unit are required")
        if not isinstance(self.value, (int, float)) or not -1e100 < self.value < 1e100:
            raise ValueError("Observation value must be finite")
        parsed = datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timestamp must have timezone")


@dataclass(frozen=True)
class Candidate:
    model: str
    output: str
    confidence: float


class ResearchRouter:
    """Invoke only explicitly injected local model callables; never autodiscover endpoints."""

    def __init__(self, models: Dict[str, Callable[[str], str]]) -> None:
        if not models:
            raise ValueError("At least one model is required")
        if any(not name or not callable(fn) for name, fn in models.items()):
            raise ValueError("Model registry must contain named callable adapters")
        self.models = dict(models)

    def deliberate(self, question: str, *, selected: Optional[Iterable[str]] = None) -> List[Candidate]:
        if not question.strip() or len(question) > 8000:
            raise ValueError("Question must be between 1 and 8000 characters")
        names = list(selected) if selected is not None else list(self.models)
        if not names or len(names) > 8 or len(set(names)) != len(names):
            raise ValueError("Select between one and eight unique models")
        if any(name not in self.models for name in names):
            raise ValueError("Unknown model; explicit registration is required")
        return [Candidate(name, str(self.models[name](question))[:16000], 0.0) for name in names]


class EvidenceJournal:
    """Append-only JSONL journal with hash chaining; not a substitute for signed audit logs."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def append(self, observation: Observation) -> str:
        observation.validate()
        if self.path.exists() and self.path.is_symlink():
            raise ValueError("Refusing symlink journal")
        previous = "0" * 64
        if self.path.exists():
            previous = self.verify()
        record = {"observation": asdict(observation), "previous": previous}
        digest = sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**record, "digest": digest}, sort_keys=True) + "\n")
        return digest

    def verify(self) -> str:
        previous = "0" * 64
        with self.path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                digest = record.pop("digest")
                if record["previous"] != previous:
                    raise ValueError("Journal chain broken")
                if sha256(json.dumps(record, sort_keys=True).encode()).hexdigest() != digest:
                    raise ValueError("Journal record tampered")
                previous = digest
        return previous


class ProposalGate:
    """Research proposals are never executed; human approval is only recorded."""

    def __init__(self) -> None:
        self.proposals: Dict[str, dict] = {}

    def propose(self, description: str, evidence_digest: str) -> str:
        if not description.strip() or len(description) > 4000:
            raise ValueError("Invalid proposal")
        if len(evidence_digest) != 64 or any(c not in "0123456789abcdef" for c in evidence_digest):
            raise ValueError("Evidence digest must be a SHA-256 hex string")
        proposal_id = sha256((description + evidence_digest).encode()).hexdigest()[:20]
        self.proposals[proposal_id] = {
            "description": description, "evidence_digest": evidence_digest,
            "status": "pending_review", "approved_by": None,
        }
        return proposal_id

    def approve(self, proposal_id: str, reviewer: str) -> None:
        if not reviewer.strip():
            raise ValueError("Named reviewer required")
        item = self.proposals[proposal_id]
        if item["status"] != "pending_review":
            raise ValueError("Proposal not pending")
        item["status"] = "approved_for_review_only"
        item["approved_by"] = reviewer


def heartbeat(journal: EvidenceJournal) -> dict:
    try:
        digest = journal.verify() if journal.path.exists() else "0" * 64
        return {"healthy": True, "journal_digest": digest, "checked_at": datetime.now(timezone.utc).isoformat()}
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return {"healthy": False, "journal_digest": None, "checked_at": datetime.now(timezone.utc).isoformat()}
