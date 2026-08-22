from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from zyra_agent import MissionBudget, MissionResult, ZyraAgent


@dataclass(frozen=True)
class AgenticProfile:
    name: str
    label: str
    max_steps: int
    max_seconds: int
    max_model_calls: int
    verification_gates: tuple[str, ...]
    max_parallel_workers: int
    max_delegation_depth: int
    human_authority_required: bool = True
    repository_scope_required: bool = True
    rollback_required: bool = True
    external_destructive_control: bool = False
    weapon_control: bool = False


MAX_PROFILE = AgenticProfile(
    name="max",
    label="ZYRA MAX",
    max_steps=32,
    max_seconds=1200,
    max_model_calls=48,
    verification_gates=("syntax", "unit", "ruff", "diff"),
    max_parallel_workers=8,
    max_delegation_depth=6,
)


@dataclass
class MaxMissionState:
    mission_id: str
    goal: str
    status: str
    started_at: float
    profile: dict[str, Any]
    operator_authorized: bool
    sleeper_mode: bool
    stages: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HumanControlError(RuntimeError):
    pass


class ZyraMaxOrchestrator:
    """High-capability repository engineering with non-bypassable human control."""

    VERSION = "MAX/1.0"

    def __init__(
        self,
        root: str | Path,
        *,
        model: str,
        profile: AgenticProfile = MAX_PROFILE,
        base_url: str = "http://127.0.0.1:11434",
        state_dir: str | Path | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.profile = profile
        self.model = model
        self.base_url = base_url
        self.state_dir = Path(state_dir or Path.home() / ".gpt-doug" / "max-missions")
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.sleeper_mode = True
        self.operator_authorized = False
        self.shutdown_latched = False

    def authorize_operator(self) -> dict[str, Any]:
        if self.shutdown_latched:
            raise HumanControlError("MAX runtime is shutdown-latched")
        self.operator_authorized = True
        return {"operator_authorized": True, "human_authority_required": True}

    def revoke_operator(self) -> dict[str, Any]:
        self.operator_authorized = False
        self.sleeper_mode = True
        return {"operator_authorized": False, "sleeper_mode": True}

    def activate(self) -> dict[str, Any]:
        if not self.operator_authorized:
            raise HumanControlError("human operator authorization is required")
        if self.shutdown_latched:
            raise HumanControlError("MAX runtime is shutdown-latched")
        self.sleeper_mode = False
        return {"sleeper_mode": False, "status": "ACTIVE"}

    def sleep(self) -> dict[str, Any]:
        self.sleeper_mode = True
        return {"sleeper_mode": True, "status": "DORMANT"}

    def emergency_shutdown(self) -> dict[str, Any]:
        self.sleeper_mode = True
        self.operator_authorized = False
        self.shutdown_latched = True
        return {
            "status": "SHUTDOWN_LATCHED",
            "sleeper_mode": True,
            "operator_authorized": False,
        }

    def reset_shutdown(self, *, human_confirmed: bool) -> dict[str, Any]:
        if not human_confirmed:
            raise HumanControlError("explicit human confirmation is required")
        self.shutdown_latched = False
        self.sleeper_mode = True
        self.operator_authorized = False
        return {"status": "RESET", "sleeper_mode": True}

    def operator_override(
        self,
        *,
        max_steps: int | None = None,
        max_seconds: int | None = None,
        max_model_calls: int | None = None,
        max_parallel_workers: int | None = None,
        max_delegation_depth: int | None = None,
    ) -> dict[str, Any]:
        if not self.operator_authorized:
            raise HumanControlError("human operator authorization is required")
        values = {
            "max_steps": max_steps,
            "max_seconds": max_seconds,
            "max_model_calls": max_model_calls,
            "max_parallel_workers": max_parallel_workers,
            "max_delegation_depth": max_delegation_depth,
        }
        clean = {k: v for k, v in values.items() if v is not None}
        for key, value in clean.items():
            if not isinstance(value, int) or value < 1:
                raise HumanControlError(f"{key} must be a positive integer")
        self.profile = replace(self.profile, **clean)
        return {
            "profile": asdict(self.profile),
            "non_bypassable": {
                "human_authority_required": True,
                "repository_scope_required": True,
                "rollback_required": True,
                "external_destructive_control": False,
                "weapon_control": False,
            },
        }

    def _agent(self) -> ZyraAgent:
        return ZyraAgent(
            self.root,
            model=self.model,
            base_url=self.base_url,
            budget=MissionBudget(
                max_steps=self.profile.max_steps,
                max_seconds=self.profile.max_seconds,
                max_model_calls=self.profile.max_model_calls,
            ),
            state_dir=self.state_dir / "agent-core",
        )

    def run(self, goal: str, *, evolve: bool = False) -> MaxMissionState:
        if self.shutdown_latched:
            raise HumanControlError("MAX runtime is shutdown-latched")
        if self.sleeper_mode:
            raise HumanControlError("MAX runtime is dormant; activate it first")
        if self.profile.human_authority_required and not self.operator_authorized:
            raise HumanControlError("human operator authorization is required")
        if not goal.strip():
            raise HumanControlError("mission goal is required")

        mission_id = f"max-{int(time.time())}"
        state = MaxMissionState(
            mission_id=mission_id,
            goal=goal.strip(),
            status="RUNNING",
            started_at=time.time(),
            profile=asdict(self.profile),
            operator_authorized=True,
            sleeper_mode=False,
        )

        agent = self._agent()
        state.stages.append({"stage": "PLAN", "status": "START"})
        preview = agent.preview(goal, evolve=evolve)
        state.stages.append({"stage": "PLAN", "status": "DONE", "preview": preview[:6000]})

        state.stages.append({"stage": "EXECUTE", "status": "START"})
        result: MissionResult = agent.run(goal, evolve=evolve)
        state.result = result.to_dict()
        state.stages.append({"stage": "EXECUTE", "status": result.status})

        if result.status != "PASS":
            state.status = "FAIL"
            self._persist(state)
            return state

        state.stages.append({
            "stage": "VERIFY",
            "status": "PASS",
            "gates": list(self.profile.verification_gates),
            "checks": result.checks,
        })
        state.status = "PASS"
        self._persist(state)
        return state

    def _persist(self, state: MaxMissionState) -> None:
        path = self.state_dir / state.mission_id / "max-mission.json"
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path.chmod(0o600)

    def status(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "profile": asdict(self.profile),
            "operator_authorized": self.operator_authorized,
            "sleeper_mode": self.sleeper_mode,
            "shutdown_latched": self.shutdown_latched,
            "no_rebellion": True,
            "repository_scope_required": True,
            "auto_rollback": True,
            "weapon_control": False,
            "external_destructive_control": False,
        }
