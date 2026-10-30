"""Bounded, auditable recovery decisions for GPT-DOUG-LLM.

The engine emits declarative recovery recommendations. It never executes shell
commands, changes files, restarts services, or deploys code by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Iterable


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HealthSignal:
    component_id: str
    state: HealthState
    observed_at: str
    details: str = ""
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryPolicy:
    max_cycles: int = 3
    max_backoff_seconds: int = 300
    require_verified_checkpoint: bool = True
    allow_automatic_low_risk_retry: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.max_cycles <= 5:
            raise ValueError("max_cycles must be between 1 and 5")
        if not 1 <= self.max_backoff_seconds <= 3600:
            raise ValueError("max_backoff_seconds must be between 1 and 3600")


@dataclass(frozen=True)
class RecoveryResult:
    component_id: str
    decision: str
    recommended_action: str
    retry_after_seconds: int
    checkpoint_id: str | None
    reason_codes: tuple[str, ...]
    audit_id: str


@dataclass
class RecoveryEngine:
    policy: RecoveryPolicy = field(default_factory=RecoveryPolicy)
    attempts: dict[str, int] = field(default_factory=dict)
    circuit_open: set[str] = field(default_factory=set)
    verified_checkpoints: dict[str, str] = field(default_factory=dict)
    audit_events: list[dict] = field(default_factory=list)

    def register_verified_checkpoint(self, component_id: str, checkpoint_id: str,
                                     integrity_digest: str) -> None:
        """Register only a checkpoint whose digest was verified by the caller."""
        if not component_id.strip() or not checkpoint_id.strip():
            raise ValueError("component_id and checkpoint_id are required")
        if len(integrity_digest) < 16:
            raise ValueError("integrity_digest must be a verified digest")
        self.verified_checkpoints[component_id] = checkpoint_id
        self._audit(component_id, "checkpoint_registered", checkpoint_id)

    def evaluate(self, signal: HealthSignal) -> RecoveryResult:
        if not signal.component_id.strip():
            raise ValueError("component_id is required")

        component = signal.component_id
        reasons: list[str] = []
        checkpoint = self.verified_checkpoints.get(component)

        if signal.state == HealthState.HEALTHY:
            self.attempts[component] = 0
            self.circuit_open.discard(component)
            decision, action, delay = "stable", "no_action", 0
            reasons.append("health_probe_healthy")
        elif component in self.circuit_open:
            decision, action, delay = "hold", "manual_diagnosis", 0
            reasons.append("circuit_breaker_open")
        elif signal.state == HealthState.DEGRADED:
            decision, action, delay = "observe", "collect_diagnostics", 0
            reasons.append("degraded_state_requires_more_evidence")
        elif signal.state == HealthState.UNKNOWN:
            decision, action, delay = "hold", "verify_health_probe", 0
            reasons.append("health_state_unknown")
        else:
            count = self.attempts.get(component, 0)
            if count >= self.policy.max_cycles:
                self.circuit_open.add(component)
                decision, action, delay = "hold", "manual_diagnosis", 0
                reasons.extend(("retry_budget_exhausted", "circuit_breaker_open"))
            elif self.policy.require_verified_checkpoint and not checkpoint:
                decision, action, delay = "hold", "create_and_verify_checkpoint"
                reasons.append("verified_checkpoint_missing")
            elif not self.policy.allow_automatic_low_risk_retry:
                decision, action, delay = "hold", "human_approval_for_retry"
                reasons.append("automatic_retry_disabled")
            else:
                self.attempts[component] = count + 1
                delay = min(2 ** count, self.policy.max_backoff_seconds)
                decision, action = "recommend", "retry_component_healthcheck"
                reasons.append("bounded_retry_recommended")

        audit_id = self._audit(component, decision, action)
        return RecoveryResult(component, decision, action, delay, checkpoint,
                              tuple(reasons), audit_id)

    def _audit(self, component_id: str, event: str, detail: str = "") -> str:
        timestamp = datetime.now(timezone.utc).isoformat()
        raw = f"{component_id}|{event}|{detail}|{timestamp}|{len(self.audit_events)}"
        audit_id = "rea:" + sha256(raw.encode()).hexdigest()[:20]
        self.audit_events.append({
            "audit_id": audit_id,
            "component_id": component_id,
            "event": event,
            "timestamp": timestamp,
        })
        return audit_id

    def snapshot(self) -> dict:
        return {
            "policy": asdict(self.policy),
            "tracked_components": sorted(set(self.attempts) | self.circuit_open),
            "open_circuits": sorted(self.circuit_open),
            "verified_checkpoint_count": len(self.verified_checkpoints),
            "audit_event_count": len(self.audit_events),
            "executes_repairs": False,
            "runs_shell_commands": False,
            "autonomous_deploy": False,
        }
