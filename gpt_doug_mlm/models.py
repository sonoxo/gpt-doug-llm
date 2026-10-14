from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Dimension(str, Enum):
    FORMAL_STATEMENT = "formal_statement"
    EQUIVALENT_FORMULATIONS = "equivalent_formulations"
    KNOWN_THEOREMS = "known_theorems"
    KNOWN_BARRIERS = "known_barriers"
    CANDIDATE_LEMMAS = "candidate_lemmas"
    COUNTEREXAMPLES = "counterexamples"
    SYMBOLIC_COMPUTATION = "symbolic_computation"
    NUMERICAL_EXPERIMENTS = "numerical_experiments"
    GEOMETRIC = "geometric"
    SPECTRAL = "spectral"
    PROBABILISTIC = "probabilistic"
    ALGEBRAIC = "algebraic"
    TOPOLOGICAL = "topological"
    SCALE_ASYMPTOTICS = "scale_asymptotics"
    FORMAL_PROOF = "formal_proof"
    INDEPENDENT_VERIFICATION = "independent_verification"


class ProofState(str, Enum):
    UNTESTED = "UNTESTED"
    NUMERICALLY_SUPPORTED = "NUMERICALLY_SUPPORTED"
    SYMBOLICALLY_VERIFIED = "SYMBOLICALLY_VERIFIED"
    LEMMA_PROVEN = "LEMMA_PROVEN"
    FORMALLY_VERIFIED = "FORMALLY_VERIFIED"
    INDEPENDENTLY_VERIFIED = "INDEPENDENTLY_VERIFIED"
    PUBLISHABLE = "PUBLISHABLE"


STATE_ORDER = [
    ProofState.UNTESTED,
    ProofState.NUMERICALLY_SUPPORTED,
    ProofState.SYMBOLICALLY_VERIFIED,
    ProofState.LEMMA_PROVEN,
    ProofState.FORMALLY_VERIFIED,
    ProofState.INDEPENDENTLY_VERIFIED,
    ProofState.PUBLISHABLE,
]


@dataclass(frozen=True)
class EvidenceRecord:
    kind: str
    source: str
    note: str
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        blob = json.dumps(
            {"kind": self.kind, "source": self.source, "note": self.note, "payload": self.payload},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class ProofClaim:
    claim_id: str
    problem: str
    statement: str
    state: ProofState = ProofState.UNTESTED
    dependencies: list[str] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    independent_verifiers: set[str] = field(default_factory=set)
    contradiction_found: bool = False

    def add_evidence(self, record: EvidenceRecord) -> None:
        if record.digest not in {item.digest for item in self.evidence}:
            self.evidence.append(record)


@dataclass(frozen=True)
class ProblemSpec:
    slug: str
    title: str
    status: str
    statement: str
    decisive_obligation: str
    dimensions: tuple[Dimension, ...]
    barriers: tuple[str, ...] = ()
    reference_url: str | None = None
