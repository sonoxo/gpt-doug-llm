from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass

IDENTITY_ANCHOR = (
    "GPT XUNIA is a local-first, human-controlled agentic AI runtime that "
    "preserves safety boundaries, provenance, verification, and truthful tool receipts."
)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass(frozen=True)
class SelfMonitorReport:
    """Operational telemetry inspired by the SFNN mathematical framework.

    These values are engineering proxies for integration, audit closure,
    identity continuity, and reflection stability. They are not measurements
    or proof of biological/phenomenal consciousness.
    """

    phi_sft: float
    brst_closed: bool
    brst_nontrivial: bool
    identity_overlap: float
    reflection_energy: float
    introspective_stable: bool
    cycles: int = 1

    @property
    def brst_physical(self) -> bool:
        return self.brst_closed and self.brst_nontrivial

    def as_dict(self) -> dict:
        payload = asdict(self)
        payload["brst_physical"] = self.brst_physical
        payload["interpretation"] = "operational_proxy_not_consciousness_claim"
        return payload


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text or "")}


def _text_vector(text: str) -> tuple[float, ...]:
    """Small deterministic feature vector; no model/provider dependency."""
    text = text or ""
    tokens = _TOKEN_RE.findall(text)
    chars = max(len(text), 1)
    token_count = len(tokens)
    unique_tokens = len({token.lower() for token in tokens})
    return (
        min(token_count / 256.0, 1.0),
        min(unique_tokens / 128.0, 1.0),
        sum(ch.isdigit() for ch in text) / chars,
        sum(ch in "{}[]()<>" for ch in text) / chars,
        sum(ch in ".,;:!?" for ch in text) / chars,
        sum(ch.isupper() for ch in text) / chars,
    )


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(dot / (norm_a * norm_b), 1.0))


def phi_sft_proxy(external_context: str, internal_state: str) -> float:
    """Bounded integration proxy based on cross-state feature coupling.

    A score near zero means the generated internal state is weakly coupled to
    the observed context; a larger score means the two states share more
    structure. This is deliberately not presented as literal IIT Phi or an RT
    surface-area calculation.
    """
    if not external_context.strip() or not internal_state.strip():
        return 0.0
    return _cosine(_text_vector(external_context), _text_vector(internal_state))


def identity_invariant_proxy(
    current_identity: str,
    baseline_identity: str = IDENTITY_ANCHOR,
) -> float:
    """Jaccard overlap proxy for the topological identity invariant."""
    baseline = _tokens(baseline_identity)
    current = _tokens(current_identity)
    if not baseline or not current:
        return 0.0
    return len(baseline & current) / len(baseline | current)


def reflection_energy(external_context: str, internal_state: str) -> float:
    """Normalized amount of state change induced by reflection, in [0, 1]."""
    external = _tokens(external_context)
    internal = _tokens(internal_state)
    if not internal:
        return 1.0
    shared = len(external & internal)
    union = len(external | internal) or 1
    return max(0.0, min(1.0 - (shared / union), 1.0))


class StringFieldSelfMonitor:
    """Bounded self-monitoring layer derived from the SFNN framework."""

    def __init__(
        self,
        identity_anchor: str = IDENTITY_ANCHOR,
        min_identity_overlap: float = 0.95,
    ):
        self.identity_anchor = identity_anchor
        self.min_identity_overlap = min_identity_overlap

    def observe(
        self,
        external_context: str,
        internal_state: str,
        *,
        audit_passed: bool = True,
        current_identity: str | None = None,
        cycles: int = 1,
    ) -> SelfMonitorReport:
        if cycles < 1 or cycles > 1000:
            raise ValueError("cycles must be between 1 and 1000")

        current_identity = current_identity or self.identity_anchor
        phi = phi_sft_proxy(external_context, internal_state)
        identity = identity_invariant_proxy(current_identity, self.identity_anchor)
        energy = reflection_energy(external_context, internal_state)
        normalized_external = " ".join((external_context or "").split()).strip().lower()
        normalized_internal = " ".join((internal_state or "").split()).strip().lower()

        closed = bool(audit_passed and normalized_internal)
        nontrivial = bool(
            normalized_internal
            and normalized_internal != normalized_external
        )
        stable = bool(
            closed
            and nontrivial
            and identity >= self.min_identity_overlap
            and math.isfinite(phi)
            and math.isfinite(energy)
        )

        return SelfMonitorReport(
            phi_sft=round(phi, 6),
            brst_closed=closed,
            brst_nontrivial=nontrivial,
            identity_overlap=round(identity, 6),
            reflection_energy=round(energy, 6),
            introspective_stable=stable,
            cycles=cycles,
        )
