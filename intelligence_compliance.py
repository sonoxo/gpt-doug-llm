"""Data-level guardrails for lawful, auditable intelligence and OSINT workflows.

The module implements the public-source baseline documented in
``docs/INTELLIGENCE_COMPLIANCE.md``.  It does not confer government status,
authority, clearance, or certification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlparse

ALLOWED_CLASSIFICATIONS = frozenset({"public", "declassified", "licensed", "user_authorized"})
ALLOWED_CLAIM_TYPES = frozenset({"fact", "inference", "assumption", "hypothesis"})
ALLOWED_CONFIDENCE = frozenset({"low", "moderate", "high"})


@dataclass(frozen=True)
class SourceProvenance:
    """Minimum provenance required for an intelligence source."""

    source_id: str
    source_type: str
    classification: str
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_url: str | None = None
    published_at: datetime | None = None


@dataclass(frozen=True)
class IntelligenceClaim:
    """Auditable analytic claim with explicit uncertainty and review state."""

    provenance: SourceProvenance
    claim: str
    claim_type: str
    confidence: str
    corroboration_count: int = 0
    limitations: tuple[str, ...] = ()
    alternatives_considered: tuple[str, ...] = ()
    privacy_review: bool = False
    operational_safety_review: bool = False
    human_approved: bool = False


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reasons: tuple[str, ...] = ()


def _valid_source_url(url: str | None) -> bool:
    if not url:
        return True
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_provenance(source: SourceProvenance) -> ValidationResult:
    """Validate that a source is usable under the public-source baseline."""

    reasons: list[str] = []
    if not source.source_id.strip():
        reasons.append("source_id is required")
    if not source.source_type.strip():
        reasons.append("source_type is required")
    if source.classification not in ALLOWED_CLASSIFICATIONS:
        reasons.append("source classification is not permitted")
    if not _valid_source_url(source.source_url):
        reasons.append("source_url must be an http(s) URL when present")
    if source.retrieved_at.tzinfo is None:
        reasons.append("retrieved_at must be timezone-aware")
    if source.published_at is not None and source.published_at.tzinfo is None:
        reasons.append("published_at must be timezone-aware when present")
    return ValidationResult(not reasons, tuple(reasons))


def validate_claim(record: IntelligenceClaim) -> ValidationResult:
    """Validate provenance, analytic labels, and minimum review metadata."""

    reasons = list(validate_provenance(record.provenance).reasons)
    if not record.claim.strip():
        reasons.append("claim is required")
    if record.claim_type not in ALLOWED_CLAIM_TYPES:
        reasons.append("claim_type is invalid")
    if record.confidence not in ALLOWED_CONFIDENCE:
        reasons.append("confidence is invalid")
    if record.corroboration_count < 0:
        reasons.append("corroboration_count cannot be negative")
    if record.claim_type != "fact" and not record.limitations:
        reasons.append("non-factual claims must record at least one limitation")
    return ValidationResult(not reasons, tuple(reasons))


def validate_claim_batch(records: Iterable[IntelligenceClaim]) -> ValidationResult:
    """Validate a batch while preserving the index of each failing record."""

    reasons: list[str] = []
    for index, record in enumerate(records):
        result = validate_claim(record)
        reasons.extend(f"record[{index}]: {reason}" for reason in result.reasons)
    return ValidationResult(not reasons, tuple(reasons))


def external_action_allowed(record: IntelligenceClaim) -> ValidationResult:
    """Require the documented review gates before an external action."""

    reasons = list(validate_claim(record).reasons)
    if not record.privacy_review:
        reasons.append("privacy review is required before external action")
    if not record.operational_safety_review:
        reasons.append("operational safety review is required before external action")
    if not record.human_approved:
        reasons.append("human approval is required before external action")
    return ValidationResult(not reasons, tuple(reasons))
