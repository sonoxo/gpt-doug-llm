"""ZYRAPALANTIR simulation-only resilience core.

This module intentionally contains no socket, HTTP, serial, PLC, SCADA, or
external-control integrations. It models synthetic assets and bounded actions
for resilience exercises inside GPT-DOUG-LLM.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List


class SafetyViolation(RuntimeError):
    """Raised when an action violates the ZYRAPALANTIR safety envelope."""


class Domain(str, Enum):
    POWER = "POWER_SIM"
    WATER = "WATER_SIM"
    TRAFFIC = "TRAFFIC_SIM"
    EMS = "EMS_SIM"
    E911 = "911_SIM"
    E988 = "988_SIM"
    AIR = "AIR_SIM"


class AssetState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    ISOLATED = "isolated"
    SAFE = "safe"
    FAILOVER = "failover"
    RESTORED = "restored"


@dataclass
class DigitalTwinAsset:
    asset_id: str
    domain: Domain
    label: str
    synthetic: bool = True
    life_safety: bool = False
    state: AssetState = AssetState.HEALTHY
    dependencies: List[str] = field(default_factory=list)
    failover_asset_id: str | None = None


@dataclass
class AuditEvent:
    timestamp: str
    action: str
    asset_id: str | None
    result: str
    approved_by_human: bool
    details: str = ""


@dataclass
class Exercise:
    exercise_id: str
    declared: bool = False
    active: bool = False
    assets: Dict[str, DigitalTwinAsset] = field(default_factory=dict)
    audit: List[AuditEvent] = field(default_factory=list)


class ZyraPalantir:
    """Simulation-only operational graph and action gateway."""

    DIVISION = "GPT-ZYRA-PALANTIR"
    CODENAME = "ZYRAPALANTIR"
    MODE = "SIMULATION_ONLY"

    ALLOWED_ACTIONS = {
        "DECLARE_EXERCISE",
        "ACKNOWLEDGE_INCIDENT",
        "ISOLATE_SIMULATED_NODE",
        "ENTER_SIMULATED_SAFE_STATE",
        "PRESERVE_LIFE_SAFETY_SERVICE",
        "ACTIVATE_SIMULATED_FAILOVER",
        "REROUTE_SIMULATED_EMS",
        "ROLLBACK_SIMULATION_ACTION",
        "RESTORE_SIMULATED_SERVICE",
        "VERIFY_RECOVERY",
        "CLOSE_EXERCISE",
    }

    def __init__(self, exercise_id: str = "zyrapalantir-demo") -> None:
        self.exercise = Exercise(exercise_id=exercise_id)

    def register_asset(self, asset: DigitalTwinAsset) -> None:
        if not asset.synthetic:
            raise SafetyViolation("ZYRAPALANTIR accepts synthetic digital-twin assets only")
        self.exercise.assets[asset.asset_id] = asset
        self._audit("REGISTER_SYNTHETIC_ASSET", asset.asset_id, "accepted", True)

    def declare_exercise(self, approved_by_human: bool) -> None:
        self._require_approval(approved_by_human)
        self.exercise.declared = True
        self.exercise.active = True
        self._audit("DECLARE_EXERCISE", None, "active", approved_by_human)

    def isolate(self, asset_id: str, approved_by_human: bool) -> None:
        self._require_active_exercise()
        self._require_approval(approved_by_human)
        asset = self._asset(asset_id)
        self._require_synthetic(asset)
        if asset.life_safety:
            raise SafetyViolation(
                "life-safety twins cannot be isolated directly; use preservation/failover logic"
            )
        asset.state = AssetState.ISOLATED
        self._audit("ISOLATE_SIMULATED_NODE", asset_id, "isolated", approved_by_human)

    def enter_safe_state(self, asset_id: str, approved_by_human: bool) -> None:
        self._require_active_exercise()
        self._require_approval(approved_by_human)
        asset = self._asset(asset_id)
        self._require_synthetic(asset)
        asset.state = AssetState.SAFE
        self._audit("ENTER_SIMULATED_SAFE_STATE", asset_id, "safe", approved_by_human)

    def activate_failover(self, asset_id: str, approved_by_human: bool) -> str:
        self._require_active_exercise()
        self._require_approval(approved_by_human)
        asset = self._asset(asset_id)
        self._require_synthetic(asset)
        if not asset.failover_asset_id:
            raise SafetyViolation(f"{asset_id} has no registered synthetic failover")
        failover = self._asset(asset.failover_asset_id)
        self._require_synthetic(failover)
        asset.state = AssetState.DEGRADED
        failover.state = AssetState.FAILOVER
        self._audit(
            "ACTIVATE_SIMULATED_FAILOVER",
            asset_id,
            "failover_active",
            approved_by_human,
            details=f"failover={failover.asset_id}",
        )
        return failover.asset_id

    def restore(self, asset_id: str, approved_by_human: bool) -> None:
        self._require_active_exercise()
        self._require_approval(approved_by_human)
        asset = self._asset(asset_id)
        self._require_synthetic(asset)
        asset.state = AssetState.RESTORED
        self._audit("RESTORE_SIMULATED_SERVICE", asset_id, "restored", approved_by_human)

    def close_exercise(self, approved_by_human: bool) -> None:
        self._require_active_exercise()
        self._require_approval(approved_by_human)
        self.exercise.active = False
        self._audit("CLOSE_EXERCISE", None, "closed", approved_by_human)

    def status(self) -> dict:
        return {
            "division": self.DIVISION,
            "codename": self.CODENAME,
            "mode": self.MODE,
            "real_infrastructure_write_access": False,
            "outbound_network_in_sim": False,
            "exercise_id": self.exercise.exercise_id,
            "exercise_active": self.exercise.active,
            "assets": {k: asdict(v) for k, v in self.exercise.assets.items()},
            "audit_events": len(self.exercise.audit),
        }

    def _asset(self, asset_id: str) -> DigitalTwinAsset:
        try:
            return self.exercise.assets[asset_id]
        except KeyError as exc:
            raise KeyError(f"unknown synthetic asset: {asset_id}") from exc

    @staticmethod
    def _require_synthetic(asset: DigitalTwinAsset) -> None:
        if not asset.synthetic:
            raise SafetyViolation("real infrastructure control is prohibited")

    @staticmethod
    def _require_approval(approved_by_human: bool) -> None:
        if not approved_by_human:
            raise SafetyViolation("human approval is required for state-changing actions")

    def _require_active_exercise(self) -> None:
        if not self.exercise.active:
            raise SafetyViolation("declare an approved simulation exercise first")

    def _audit(
        self,
        action: str,
        asset_id: str | None,
        result: str,
        approved_by_human: bool,
        details: str = "",
    ) -> None:
        self.exercise.audit.append(
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=action,
                asset_id=asset_id,
                result=result,
                approved_by_human=approved_by_human,
                details=details,
            )
        )


def demo_graph() -> ZyraPalantir:
    """Return a tiny synthetic dependency graph suitable for local tests."""
    z = ZyraPalantir("demo-resilience-exercise")
    z.register_asset(
        DigitalTwinAsset(
            "power-primary",
            Domain.POWER,
            "Synthetic primary power node",
            failover_asset_id="power-backup",
        )
    )
    z.register_asset(
        DigitalTwinAsset("power-backup", Domain.POWER, "Synthetic backup power node")
    )
    z.register_asset(
        DigitalTwinAsset(
            "hospital-twin",
            Domain.EMS,
            "Synthetic hospital life-safety service",
            life_safety=True,
            dependencies=["power-primary"],
        )
    )
    z.register_asset(
        DigitalTwinAsset(
            "traffic-07",
            Domain.TRAFFIC,
            "Synthetic intersection controller 07",
        )
    )
    return z
