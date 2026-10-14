from __future__ import annotations

from dataclasses import dataclass

from .models import EvidenceRecord, ProofClaim, ProofState, STATE_ORDER


@dataclass(frozen=True)
class ProofEdge:
    source: str
    relation: str
    target: str


class ProofGraph:
    """A fail-closed proof hypergraph with explicit evidence-gated promotions."""

    def __init__(self) -> None:
        self.claims: dict[str, ProofClaim] = {}
        self.edges: list[ProofEdge] = []

    def add_claim(self, claim: ProofClaim) -> None:
        if claim.claim_id in self.claims:
            raise ValueError(f"duplicate claim: {claim.claim_id}")
        self.claims[claim.claim_id] = claim

    def add_edge(self, source: str, relation: str, target: str) -> None:
        if source not in self.claims or target not in self.claims:
            raise KeyError("both edge endpoints must exist")
        self.edges.append(ProofEdge(source=source, relation=relation, target=target))

    def add_evidence(self, claim_id: str, evidence: EvidenceRecord) -> None:
        self.claims[claim_id].add_evidence(evidence)

    def add_verifier(self, claim_id: str, verifier_id: str) -> None:
        if not verifier_id.strip():
            raise ValueError("verifier id cannot be empty")
        self.claims[claim_id].independent_verifiers.add(verifier_id.strip())

    def mark_contradiction(self, claim_id: str) -> None:
        self.claims[claim_id].contradiction_found = True

    def _evidence_kinds(self, claim: ProofClaim) -> set[str]:
        return {item.kind for item in claim.evidence}

    def _check_gate(self, claim: ProofClaim, target: ProofState) -> None:
        if claim.contradiction_found:
            raise ValueError("claim has an unresolved contradiction")

        current_index = STATE_ORDER.index(claim.state)
        target_index = STATE_ORDER.index(target)
        if target_index != current_index + 1:
            raise ValueError("proof states must advance exactly one gate at a time")

        kinds = self._evidence_kinds(claim)
        if target is ProofState.NUMERICALLY_SUPPORTED and "numerical" not in kinds:
            raise ValueError("numerical evidence required")
        if target is ProofState.SYMBOLICALLY_VERIFIED and "symbolic" not in kinds:
            raise ValueError("symbolic evidence required")
        if target is ProofState.LEMMA_PROVEN and "proof" not in kinds:
            raise ValueError("human-readable proof evidence required")
        if target is ProofState.FORMALLY_VERIFIED and "formal" not in kinds:
            raise ValueError("formal proof-checker evidence required")
        if target is ProofState.INDEPENDENTLY_VERIFIED and len(claim.independent_verifiers) < 2:
            raise ValueError("at least two independent verifiers are required")
        if target is ProofState.PUBLISHABLE and "adversarial_review" not in kinds:
            raise ValueError("adversarial review evidence required")

    def promote(self, claim_id: str, target: ProofState) -> ProofClaim:
        claim = self.claims[claim_id]
        self._check_gate(claim, target)
        claim.state = target
        return claim

    def snapshot(self) -> dict:
        return {
            "claims": [
                {
                    "id": claim.claim_id,
                    "problem": claim.problem,
                    "statement": claim.statement,
                    "state": claim.state.value,
                    "dependencies": list(claim.dependencies),
                    "evidence_digests": [item.digest for item in claim.evidence],
                    "independent_verifiers": sorted(claim.independent_verifiers),
                    "contradiction_found": claim.contradiction_found,
                }
                for claim in self.claims.values()
            ],
            "edges": [edge.__dict__ for edge in self.edges],
        }
