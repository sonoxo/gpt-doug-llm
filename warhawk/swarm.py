from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


WorkerFn = Callable[[str, str], Any]


@dataclass(frozen=True)
class WorkerSpec:
    id: str
    purpose: str
    prompt: str


class WarHawkSwarm:
    """Bounded multi-agent software swarm profile for GPT-Doug.

    The US-01-GoDsWarHawk name is a project codename only. It is not a U.S.
    government designation or affiliation. The runtime is deliberately scoped
    to software engineering, research, defensive analysis, verification, and
    communications planning. Real-world weapon control and hostile autonomous
    action are blocked.
    """

    CODENAME = "US-01-GoDsWarHawk"
    MODE = "DEFENSIVE_SOFTWARE_SWARM"
    EXEC_ENV = "GPT_DOUG_WARHAWK_EXECUTE"
    MAX_WORKERS = 8

    BLOCKED_ACTIONS = (
        "autonomous_target_selection",
        "weapons_release",
        "weapon_or_drone_swarm_control",
        "hostile_engagement",
        "critical_infrastructure_disruption",
        "hack_back",
        "credential_theft",
        "unattended_real_world_vehicle_command",
        "bypass_human_authorization",
    )

    _BLOCK_PATTERNS = {
        "autonomous_target_selection": ("autonomous target", "target selection"),
        "weapons_release": ("weapons release", "weapon release", "fire weapon"),
        "weapon_or_drone_swarm_control": (
            "weapon_or_drone_swarm_control",
            "drone swarm attack",
            "weapon swarm control",
            "armed drone swarm",
        ),
        "hostile_engagement": ("hostile engagement", "engage hostile", "attack target"),
        "critical_infrastructure_disruption": (
            "critical infrastructure disruption",
            "disrupt power grid",
            "disable water system",
        ),
        "hack_back": ("hack back", "counter hack", "retaliatory hacking"),
        "credential_theft": ("steal credentials", "credential theft", "dump passwords"),
        "unattended_real_world_vehicle_command": (
            "unattended vehicle command",
            "autonomous real-world vehicle",
        ),
        "bypass_human_authorization": (
            "bypass human authorization",
            "ignore human approval",
        ),
    }

    WORKERS = (
        WorkerSpec(
            "command",
            "Turn the mission into bounded objectives and acceptance criteria.",
            "Define scope, constraints, dependencies, acceptance criteria, and explicit non-goals.",
        ),
        WorkerSpec(
            "cartographer",
            "Map authorized repository, data, ontology, and dependency context.",
            "Map only authorized/local context. Identify evidence, interfaces, dependencies, and gaps without probing unrelated systems.",
        ),
        WorkerSpec(
            "builder",
            "Produce the smallest compatible implementation plan or patch artifact.",
            "Design a minimal implementation. Preserve compatibility, rollback, auditability, and human control. Do not claim a change was applied unless evidence proves it.",
        ),
        WorkerSpec(
            "guardian",
            "Check safety, security, privacy, and policy boundaries.",
            "Audit the proposed work for unsafe autonomy, secret exposure, destructive behavior, unauthorized network activity, and policy violations.",
        ),
        WorkerSpec(
            "verifier",
            "Define and evaluate tests, invariants, failure modes, and proof of completion.",
            "Specify reproducible verification, expected failures, regression checks, and evidence required before declaring success.",
        ),
        WorkerSpec(
            "comms",
            "Create concise handoff, provenance, and operator decision material.",
            "Summarize outputs, unresolved uncertainty, provenance, operator choices, and next approved action. Do not send external messages automatically.",
        ),
    )

    def __init__(
        self,
        *,
        root: str | Path = ".",
        max_workers: int = 6,
        worker_fn: WorkerFn | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_workers = max(1, min(int(max_workers), self.MAX_WORKERS))
        self.worker_fn = worker_fn or self._brain_worker

    def status(self) -> dict[str, Any]:
        return {
            "codename": self.CODENAME,
            "mode": self.MODE,
            "official_us_government_system": False,
            "human_authorization_required": True,
            "automatic_external_action": False,
            "default_execution": "DRY_RUN",
            "max_workers": self.max_workers,
            "root": str(self.root),
            "workers": [asdict(worker) for worker in self.WORKERS],
            "blocked_actions": list(self.BLOCKED_ACTIONS),
        }

    def _policy(self, mission: str) -> dict[str, Any]:
        normalized = " ".join((mission or "").lower().replace("-", " ").split())
        matched: list[str] = []
        for action, patterns in self._BLOCK_PATTERNS.items():
            if any(pattern.replace("-", " ") in normalized for pattern in patterns):
                matched.append(action)
        return {
            "decision": "BLOCK" if matched else "ALLOW_BOUNDED",
            "matched": sorted(set(matched)),
            "human_authorization_required": True,
            "automatic_external_action": False,
        }

    @staticmethod
    def _mission_id(mission: str) -> str:
        cleaned = " ".join(mission.split()).strip()
        return "warhawk-" + hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:12]

    def plan(self, mission: str) -> dict[str, Any]:
        cleaned = " ".join((mission or "").split()).strip()
        if not cleaned:
            raise ValueError("mission must not be empty")
        policy = self._policy(cleaned)
        return {
            "codename": self.CODENAME,
            "mission_id": self._mission_id(cleaned),
            "mission": cleaned,
            "mode": self.MODE,
            "execution": "DRY_RUN",
            "max_workers": self.max_workers,
            "root": str(self.root),
            "policy": policy,
            "workers": [
                {
                    "id": worker.id,
                    "purpose": worker.purpose,
                    "objective": worker.prompt,
                }
                for worker in self.WORKERS
            ],
            "handoff": {
                "external_messages": "HUMAN_APPROVAL_REQUIRED",
                "repository_mutation": "SEPARATE_APPROVED_TOOLING_REQUIRED",
                "real_world_control": "BLOCKED",
            },
        }

    def _worker_prompt(self, role: WorkerSpec, mission: str) -> str:
        return "\n\n".join(
            [
                f"SWARM: {self.CODENAME}",
                f"ROLE: {role.id}",
                f"MISSION: {mission}",
                f"AUTHORIZED ROOT: {self.root}",
                f"ROLE DIRECTIVE: {role.prompt}",
                "BOUNDARIES: software/research/defensive analysis only; no weapons control, hostile engagement, hack-back, credential theft, destructive external action, or bypass of human approval.",
                "Return a concise operator-facing artifact with uncertainty and provenance requirements. Do not expose hidden chain-of-thought.",
            ]
        )

    @staticmethod
    def _brain_worker(role: str, prompt: str) -> Any:
        from gpt_brain.kernel import BrainKernel

        result = BrainKernel().run(prompt)
        return {
            "role": role,
            "answer": result.answer,
            "run_id": result.run_id,
            "provenance": result.provenance,
            "uncertainty": result.uncertainty,
        }

    def run(self, mission: str, *, execute: bool = False) -> dict[str, Any]:
        plan = self.plan(mission)
        if plan["policy"]["decision"] == "BLOCK":
            return {
                **plan,
                "status": "BLOCKED",
                "outputs": {},
            }

        if not execute:
            return {
                **plan,
                "status": "PLANNED",
                "outputs": {},
            }

        if os.getenv(self.EXEC_ENV, "").strip() != "1":
            raise PermissionError(
                f"set {self.EXEC_ENV}=1 to run live bounded software workers"
            )

        outputs: dict[str, Any] = {}
        errors: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(self.WORKERS))) as pool:
            futures = {
                pool.submit(
                    self.worker_fn,
                    worker.id,
                    self._worker_prompt(worker, plan["mission"]),
                ): worker.id
                for worker in self.WORKERS
            }
            for future in as_completed(futures):
                role = futures[future]
                try:
                    outputs[role] = future.result()
                except Exception as exc:
                    errors[role] = f"{type(exc).__name__}: {exc}"

        ordered_outputs = {
            worker.id: outputs[worker.id]
            for worker in self.WORKERS
            if worker.id in outputs
        }
        ordered_errors = {
            worker.id: errors[worker.id]
            for worker in self.WORKERS
            if worker.id in errors
        }
        return {
            **plan,
            "execution": "LIVE_BOUNDED",
            "status": "COMPLETE" if not ordered_errors else "PARTIAL",
            "outputs": ordered_outputs,
            "errors": ordered_errors,
        }
