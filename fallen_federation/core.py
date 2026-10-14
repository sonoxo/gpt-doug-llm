"""Governed research-swarm federation for GPT-Doug.

This module intentionally does not self-propagate, scan networks, bypass repository
permissions, or control physical systems. It plans work only for repositories and
data sources that are explicitly authorized in a manifest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

MAX_WORKERS = 555


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    role: str
    enabled: bool = True


@dataclass(frozen=True)
class RepositoryTarget:
    repository: str
    authorized: bool
    integration_mode: str = "pull_request"

    def validate(self) -> None:
        if "/" not in self.repository:
            raise ValueError("repository must be owner/name")
        if not self.authorized:
            raise PermissionError(f"repository not authorized: {self.repository}")
        if self.integration_mode not in {"pull_request", "read_only"}:
            raise ValueError("integration_mode must be pull_request or read_only")


@dataclass(frozen=True)
class FederationPolicy:
    max_workers: int = MAX_WORKERS
    require_human_merge: bool = True
    allow_self_propagation: bool = False
    allow_physical_actuation: bool = False
    allow_private_bio_data: bool = False

    def validate(self) -> None:
        if not 1 <= self.max_workers <= MAX_WORKERS:
            raise ValueError(f"max_workers must be 1..{MAX_WORKERS}")
        if self.allow_self_propagation:
            raise ValueError("self propagation is not supported")
        if self.allow_physical_actuation:
            raise ValueError("physical actuation is not supported")


@dataclass
class Federation:
    policy: FederationPolicy
    workers: list[WorkerSpec] = field(default_factory=list)
    repositories: list[RepositoryTarget] = field(default_factory=list)

    def validate(self) -> None:
        self.policy.validate()
        if len(self.workers) > self.policy.max_workers:
            raise ValueError("worker count exceeds policy")
        for target in self.repositories:
            target.validate()

    def deployment_plan(self) -> list[dict]:
        self.validate()
        enabled = [w for w in self.workers if w.enabled]
        plan: list[dict] = []
        for target in self.repositories:
            plan.append(
                {
                    "repository": target.repository,
                    "mode": target.integration_mode,
                    "workers": len(enabled),
                    "human_merge_required": self.policy.require_human_merge,
                    "status": "READY_FOR_AUTHORIZED_INTEGRATION",
                }
            )
        return plan


def default_workers() -> list[WorkerSpec]:
    """Build a bounded 555-worker portfolio without spawning processes."""
    roles = [
        "discovery",
        "evidence_verification",
        "experimental_design",
        "replication_adversarial",
        "translation_deployment",
    ]
    workers: list[WorkerSpec] = []
    for role in roles:
        for index in range(111):
            workers.append(WorkerSpec(name=f"{role}-{index + 1:03d}", role=role))
    return workers


def repositories_from_names(names: Iterable[str]) -> list[RepositoryTarget]:
    return [RepositoryTarget(repository=name, authorized=True) for name in names]
