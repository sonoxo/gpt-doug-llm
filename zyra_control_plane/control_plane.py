"""Integrated ZYRA Mission Control orchestration."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Callable

from .attestation import AttestationSigner
from .capabilities import WRITE_LOCAL, CapabilityRegistry, MissionGrant
from .dag import MissionDAG, MissionStep, StepResult
from .journal import MissionJournal


class MissionControl:
    """Coordinates policy snapshots, DAG execution, journaling, and attestations."""

    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.journal = MissionJournal(self.state_dir / "mission-events.jsonl")
        self.registry = CapabilityRegistry()
        self.signer = AttestationSigner(self.state_dir / "attestation.key")
        self.checkpoint_dir = self.state_dir / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.attestation_dir = self.state_dir / "attestations"
        self.attestation_dir.mkdir(parents=True, exist_ok=True)

    def new_mission(
        self,
        goal: str,
        dag: MissionDAG,
        *,
        grant: MissionGrant = WRITE_LOCAL,
        model_route: str = "gpt-doug-core",
    ) -> dict[str, Any]:
        mission_id = uuid.uuid4().hex[:12]
        criteria = dag.acceptance_criteria()
        self.journal.append(mission_id, "MISSION_CREATED", data={"goal": goal, "model_route": model_route})
        self.journal.policy_snapshot(mission_id, self.registry.snapshot(grant))
        self.journal.append(mission_id, "ACCEPTANCE_LOCKED", data={"criteria": criteria})
        self.journal.append(mission_id, "PLAN_CREATED", data=dag.plan())
        return {"mission_id": mission_id, "goal": goal, "grant": grant, "model_route": model_route, "dag": dag}

    def record_patch_preview(self, mission_id: str, diffs: dict[str, str]) -> dict[str, Any]:
        bounded = {path: text[:50000] for path, text in sorted(diffs.items())}
        return self.journal.append(
            mission_id,
            "PATCH_PREVIEW",
            data={"files": bounded, "file_count": len(bounded)},
        )

    def save_checkpoint(self, mission_id: str, completed_steps: set[str]) -> Path:
        target = self.checkpoint_dir / f"{mission_id}.json"
        payload = {
            "mission_id": mission_id,
            "completed_steps": sorted(completed_steps),
            "journal_head": self.journal.head().digest,
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.journal.append(
            mission_id,
            "CHECKPOINT_SAVED",
            data={"path": str(target), "completed_steps": sorted(completed_steps)},
        )
        return target

    def load_checkpoint(self, mission_id: str) -> set[str]:
        target = self.checkpoint_dir / f"{mission_id}.json"
        if not target.exists():
            return set()
        payload = json.loads(target.read_text(encoding="utf-8"))
        return set(payload.get("completed_steps", []))

    def execute(
        self,
        mission: dict[str, Any],
        executors: dict[str, Callable[[MissionStep], StepResult]],
        *,
        resume: bool = False,
    ) -> dict[str, Any]:
        mission_id = str(mission["mission_id"])
        dag: MissionDAG = mission["dag"]
        grant: MissionGrant = mission["grant"]
        completed = self.load_checkpoint(mission_id) if resume else set()

        def runner(step: MissionStep) -> StepResult:
            ok, missing = self.registry.authorize(step.executor, grant, step.capabilities)
            if not ok:
                self.journal.append(
                    mission_id,
                    "STEP_BLOCKED",
                    data={"step_id": step.step_id, "missing": list(missing)},
                    failure_type="tool",
                )
                return StepResult(step.step_id, False, f"capability denied: {', '.join(missing)}")
            executor = executors.get(step.executor)
            if executor is None:
                self.journal.append(
                    mission_id,
                    "STEP_FAILED",
                    data={"step_id": step.step_id, "reason": "executor unavailable"},
                    failure_type="runtime",
                )
                return StepResult(step.step_id, False, "executor unavailable")
            self.journal.append(mission_id, "STEP_STARTED", data={"step_id": step.step_id, "executor": step.executor})
            result = executor(step)
            self.journal.append(
                mission_id,
                "STEP_VERIFIED" if result.ok else "STEP_FAILED",
                data={"step_id": step.step_id, "detail": result.detail, "evidence": result.evidence},
                duration_ms=result.duration_ms,
                failure_type=None if result.ok else "validation",
            )
            return result

        results = dag.execute(runner, resume_after=completed)
        completed_now = {step_id for step_id, result in results.items() if result.ok}
        self.save_checkpoint(mission_id, completed_now)
        verified = len(results) == len(dag.steps) and all(result.ok for result in results.values())
        self.journal.append(
            mission_id,
            "MISSION_VERIFIED" if verified else "MISSION_FAILED",
            data={"verified": verified, "results": {key: value.to_dict() for key, value in results.items()}},
            failure_type=None if verified else "review",
        )
        return {"mission_id": mission_id, "verified": verified, "results": {key: value.to_dict() for key, value in results.items()}}

    def attest(
        self,
        mission: dict[str, Any],
        result: dict[str, Any],
        *,
        commit_sha: str | None = None,
        changed_files: list[str] | None = None,
        checks: list[dict[str, Any]] | None = None,
        artifact_digest: str | None = None,
        sbom_digest: str | None = None,
    ) -> dict[str, Any]:
        attestation = self.signer.sign(
            mission_id=mission["mission_id"],
            prompt=mission["goal"],
            commit_sha=commit_sha,
            model_route=mission["model_route"],
            changed_files=changed_files or [],
            checks=checks or [{"name": "mission", "ok": bool(result.get("verified"))}],
            journal_head=self.journal.head().digest,
            artifact_digest=artifact_digest,
            sbom_digest=sbom_digest,
        )
        path = self.attestation_dir / f"{mission['mission_id']}.json"
        self.signer.write(path, attestation)
        self.journal.append(
            mission["mission_id"],
            "ATTESTATION_CREATED",
            data={"path": str(path), "digest": attestation["digest"]},
        )
        return attestation

    def status(self) -> dict[str, Any]:
        verification = self.journal.verify()
        return {
            "journal": verification,
            "journal_path": str(self.journal.path),
            "capabilities": self.registry.all(),
            "checkpoints": len(list(self.checkpoint_dir.glob("*.json"))),
            "attestations": len(list(self.attestation_dir.glob("*.json"))),
        }
