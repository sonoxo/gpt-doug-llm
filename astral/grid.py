"""GPT-DOUG // XUNIA Astral Grid v2.

Governed software resource orchestration with multi-resource admission control,
peer assist, leases, depletion-aware rebalancing, quarantine, and tamper-evident
audit chaining.

This module models software compute/resource orchestration only. It does not
control vehicles, weapons, physical power transfer, or other real-world actuation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Iterable, Mapping


XUNIA_PUBLIC_BASE = "https://xunia.org"
ASTRAL_SCHEMA = "xunia.astral-grid.v2"
EPSILON = 1e-9


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_resources(values: Mapping[str, float]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for name, value in values.items():
        key = str(name).strip().lower()
        amount = float(value)
        if not key:
            raise ValueError("resource names must be non-empty")
        if amount < 0:
            raise ValueError(f"resource '{key}' must be non-negative")
        cleaned[key] = amount
    return cleaned


@dataclass(slots=True)
class ResourceNode:
    node_id: str
    capacity: dict[str, float]
    usage: dict[str, float] = field(default_factory=dict)
    health: float = 1.0
    authorized: bool = True
    dependency_status: str = "ready"
    labels: set[str] = field(default_factory=set)
    zone: str = "default"
    quarantined: bool = False
    generation: int = 0

    def __post_init__(self) -> None:
        self.capacity = _clean_resources(self.capacity)
        self.usage = _clean_resources(self.usage)
        if not self.capacity or any(value <= 0 for value in self.capacity.values()):
            raise ValueError("node capacity must contain positive resources")
        unknown = set(self.usage) - set(self.capacity)
        if unknown:
            raise ValueError(f"usage references unknown resources: {sorted(unknown)}")
        for name, value in self.usage.items():
            if value > self.capacity[name] + EPSILON:
                raise ValueError(f"usage exceeds capacity for resource '{name}'")
        self.health = min(max(float(self.health), 0.0), 1.0)
        self.labels = {str(label).strip().lower() for label in self.labels if str(label).strip()}
        self.zone = self.zone.strip() or "default"

    @property
    def healthy(self) -> bool:
        return self.health >= 0.5

    @property
    def ready(self) -> bool:
        return (
            self.authorized
            and self.healthy
            and not self.quarantined
            and self.dependency_status == "ready"
        )

    def available(self, resource: str) -> float:
        return max(0.0, self.capacity.get(resource, 0.0) - self.usage.get(resource, 0.0))

    def headroom_ratio(self, resource: str) -> float:
        capacity = self.capacity.get(resource, 0.0)
        if capacity <= 0:
            return 0.0
        return self.available(resource) / capacity


@dataclass(slots=True)
class Task:
    task_id: str
    requirements: dict[str, float]
    priority: int = 50
    required_labels: set[str] = field(default_factory=set)
    required_zone: str | None = None
    shareable_resources: set[str] = field(default_factory=lambda: {"compute"})
    max_helpers: int = 3
    lease_seconds: int = 900
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.requirements = _clean_resources(self.requirements)
        if not self.requirements or not any(value > 0 for value in self.requirements.values()):
            raise ValueError("task requirements must request at least one resource")
        self.priority = min(max(int(self.priority), 0), 100)
        self.required_labels = {
            str(label).strip().lower() for label in self.required_labels if str(label).strip()
        }
        self.shareable_resources = {
            str(name).strip().lower() for name in self.shareable_resources if str(name).strip()
        }
        self.max_helpers = min(max(int(self.max_helpers), 0), 16)
        self.lease_seconds = min(max(int(self.lease_seconds), 1), 86_400)


@dataclass(slots=True)
class Assignment:
    task_id: str
    primary_node: str
    helper_nodes: list[str]
    reservations: dict[str, dict[str, float]]
    score: float
    lease_id: str
    created_at: str
    expires_at: str
    state: str = "reserved"


class AstralGrid:
    """Fail-closed, auditable multi-resource software scheduler."""

    def __init__(self, *, depletion_threshold: float = 0.15) -> None:
        if not 0 <= depletion_threshold < 1:
            raise ValueError("depletion_threshold must be in [0, 1)")
        self.nodes: dict[str, ResourceNode] = {}
        self.assignments: dict[str, Assignment] = {}
        self.audit: list[dict[str, object]] = []
        self.depletion_threshold = float(depletion_threshold)

    def _record(self, event: str, **payload: object) -> dict[str, object]:
        previous_hash = self.audit[-1]["hash"] if self.audit else "GENESIS"
        record: dict[str, object] = {
            "seq": len(self.audit) + 1,
            "ts": _utcnow().isoformat(),
            "event": event,
            "prev_hash": previous_hash,
            **payload,
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        record["hash"] = sha256(canonical.encode("utf-8")).hexdigest()
        self.audit.append(record)
        return record

    def verify_audit_chain(self) -> bool:
        previous = "GENESIS"
        for expected_seq, stored in enumerate(self.audit, start=1):
            if stored.get("seq") != expected_seq or stored.get("prev_hash") != previous:
                return False
            candidate = dict(stored)
            expected_hash = candidate.pop("hash", None)
            canonical = json.dumps(candidate, sort_keys=True, separators=(",", ":"), default=str)
            actual_hash = sha256(canonical.encode("utf-8")).hexdigest()
            if expected_hash != actual_hash:
                return False
            previous = str(expected_hash)
        return True

    def register(self, node: ResourceNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"node '{node.node_id}' already exists")
        self.nodes[node.node_id] = node
        self._record(
            "node.registered",
            node_id=node.node_id,
            capacity=node.capacity,
            labels=sorted(node.labels),
            zone=node.zone,
        )

    def update_node(
        self,
        node_id: str,
        *,
        usage: Mapping[str, float] | None = None,
        health: float | None = None,
        authorized: bool | None = None,
        dependency_status: str | None = None,
        quarantined: bool | None = None,
    ) -> None:
        node = self.nodes[node_id]
        if usage is not None:
            cleaned = _clean_resources(usage)
            unknown = set(cleaned) - set(node.capacity)
            if unknown:
                raise ValueError(f"usage references unknown resources: {sorted(unknown)}")
            for resource, value in cleaned.items():
                if value > node.capacity[resource] + EPSILON:
                    raise ValueError(f"usage exceeds capacity for resource '{resource}'")
            node.usage.update(cleaned)
        if health is not None:
            node.health = min(max(float(health), 0.0), 1.0)
        if authorized is not None:
            node.authorized = bool(authorized)
        if dependency_status is not None:
            node.dependency_status = dependency_status.strip().lower() or "unknown"
        if quarantined is not None:
            node.quarantined = bool(quarantined)
        node.generation += 1
        self._record(
            "node.updated",
            node_id=node_id,
            usage=node.usage,
            health=node.health,
            authorized=node.authorized,
            dependency_status=node.dependency_status,
            quarantined=node.quarantined,
            generation=node.generation,
        )

    def quarantine(self, node_id: str, *, reason: str) -> None:
        node = self.nodes[node_id]
        node.quarantined = True
        node.generation += 1
        self._record("node.quarantined", node_id=node_id, reason=reason)

    def unquarantine(self, node_id: str, *, reason: str) -> None:
        node = self.nodes[node_id]
        node.quarantined = False
        node.generation += 1
        self._record("node.unquarantined", node_id=node_id, reason=reason)

    def _eligible(self, task: Task, *, exclude: set[str] | None = None) -> list[ResourceNode]:
        excluded = exclude or set()
        return [
            node
            for node in self.nodes.values()
            if node.node_id not in excluded
            and node.ready
            and task.required_labels.issubset(node.labels)
            and (task.required_zone is None or node.zone == task.required_zone)
        ]

    @staticmethod
    def _score(node: ResourceNode, task: Task) -> float:
        ratios: list[float] = []
        for resource, required in task.requirements.items():
            if required <= 0:
                continue
            ratios.append(min(node.available(resource) / required, 2.0))
        fit = sum(ratios) / len(ratios) if ratios else 0.0
        utilization = 0.0
        if node.capacity:
            utilization = sum(
                node.usage.get(name, 0.0) / cap for name, cap in node.capacity.items()
            ) / len(node.capacity)
        priority_weight = task.priority / 100.0
        return node.health * 0.40 + fit * 0.35 + (1.0 - utilization) * 0.20 + priority_weight * 0.05

    def _primary_can_host_nonshareable(self, node: ResourceNode, task: Task) -> bool:
        for resource, required in task.requirements.items():
            if resource not in task.shareable_resources and node.available(resource) + EPSILON < required:
                return False
        return True

    def plan(
        self,
        task: Task,
        *,
        allow_peer_assist: bool = True,
        exclude: set[str] | None = None,
    ) -> dict[str, object]:
        eligible = sorted(
            self._eligible(task, exclude=exclude),
            key=lambda node: self._score(node, task),
            reverse=True,
        )
        primaries = [node for node in eligible if self._primary_can_host_nonshareable(node, task)]
        if not primaries:
            reason = "no_primary_satisfies_nonshareable_requirements"
            self._record("task.plan_rejected", task_id=task.task_id, reason=reason)
            raise RuntimeError(reason)

        for primary in primaries:
            reservations: dict[str, dict[str, float]] = {primary.node_id: {}}
            remaining = dict(task.requirements)

            for resource, required in task.requirements.items():
                if resource not in task.shareable_resources:
                    reservations[primary.node_id][resource] = required
                    remaining[resource] = 0.0
                    continue
                amount = min(primary.available(resource), required)
                if amount > 0:
                    reservations[primary.node_id][resource] = amount
                    remaining[resource] -= amount

            helper_count = 0
            if allow_peer_assist:
                for helper in eligible:
                    if helper.node_id == primary.node_id or helper_count >= task.max_helpers:
                        continue
                    contribution: dict[str, float] = {}
                    for resource, needed in remaining.items():
                        if needed <= EPSILON or resource not in task.shareable_resources:
                            continue
                        amount = min(helper.available(resource), needed)
                        if amount > 0:
                            contribution[resource] = amount
                            remaining[resource] -= amount
                    if contribution:
                        reservations[helper.node_id] = contribution
                        helper_count += 1
                    if all(value <= EPSILON for value in remaining.values()):
                        break

            if all(value <= EPSILON for value in remaining.values()):
                return {
                    "primary_node": primary.node_id,
                    "helper_nodes": [node_id for node_id in reservations if node_id != primary.node_id],
                    "reservations": reservations,
                    "score": self._score(primary, task),
                }

        reason = "insufficient_authorized_capacity"
        self._record(
            "task.plan_rejected",
            task_id=task.task_id,
            reason=reason,
            requirements=task.requirements,
        )
        raise RuntimeError(reason)

    def assign(
        self,
        task: Task,
        *,
        allow_peer_assist: bool = True,
        exclude: set[str] | None = None,
    ) -> Assignment:
        if task.task_id in self.assignments and self.assignments[task.task_id].state == "reserved":
            raise RuntimeError(f"task '{task.task_id}' already has an active reservation")

        plan = self.plan(task, allow_peer_assist=allow_peer_assist, exclude=exclude)
        reservations = plan["reservations"]
        assert isinstance(reservations, dict)

        # Atomic admission check: no state mutates until every reservation still fits.
        for node_id, bundle in reservations.items():
            node = self.nodes[node_id]
            for resource, amount in bundle.items():
                if node.available(resource) + EPSILON < amount:
                    self._record(
                        "task.race_rejected",
                        task_id=task.task_id,
                        node_id=node_id,
                        resource=resource,
                    )
                    raise RuntimeError("resource state changed during admission")

        for node_id, bundle in reservations.items():
            node = self.nodes[node_id]
            for resource, amount in bundle.items():
                node.usage[resource] = node.usage.get(resource, 0.0) + amount

        created = _utcnow()
        expires = created + timedelta(seconds=task.lease_seconds)
        lease_material = f"{task.task_id}|{created.isoformat()}|{plan['primary_node']}"
        lease_id = sha256(lease_material.encode("utf-8")).hexdigest()[:20]
        assignment = Assignment(
            task_id=task.task_id,
            primary_node=str(plan["primary_node"]),
            helper_nodes=list(plan["helper_nodes"]),
            reservations={
                node_id: {resource: float(amount) for resource, amount in bundle.items()}
                for node_id, bundle in reservations.items()
            },
            score=float(plan["score"]),
            lease_id=lease_id,
            created_at=created.isoformat(),
            expires_at=expires.isoformat(),
        )
        self.assignments[task.task_id] = assignment
        self._record(
            "task.assigned",
            task_id=task.task_id,
            primary_node=assignment.primary_node,
            helper_nodes=assignment.helper_nodes,
            reservations=assignment.reservations,
            score=round(assignment.score, 5),
            lease_id=assignment.lease_id,
            expires_at=assignment.expires_at,
        )
        return assignment

    def release(self, assignment: Assignment, *, reason: str = "complete") -> None:
        if assignment.state != "reserved":
            return
        for node_id, bundle in assignment.reservations.items():
            node = self.nodes.get(node_id)
            if node is None:
                continue
            for resource, amount in bundle.items():
                node.usage[resource] = max(0.0, node.usage.get(resource, 0.0) - amount)
        assignment.state = "released"
        self._record(
            "task.released",
            task_id=assignment.task_id,
            lease_id=assignment.lease_id,
            reason=reason,
        )

    def expire_leases(self, *, now: datetime | None = None) -> list[str]:
        moment = now or _utcnow()
        expired: list[str] = []
        for assignment in list(self.assignments.values()):
            if assignment.state != "reserved":
                continue
            expires = datetime.fromisoformat(assignment.expires_at)
            if expires <= moment:
                expired.append(assignment.task_id)
                self.release(assignment, reason="lease_expired")
        return expired

    def depleted(self, node_id: str) -> bool:
        node = self.nodes[node_id]
        if not node.ready:
            return True
        active_resources = [name for name, cap in node.capacity.items() if cap > 0]
        return any(node.headroom_ratio(resource) < self.depletion_threshold for resource in active_resources)

    def rebalance(self, task: Task) -> Assignment:
        current = self.assignments.get(task.task_id)
        if current is None or current.state != "reserved":
            return self.assign(task)
        if not self.depleted(current.primary_node):
            return current

        previous_primary = current.primary_node
        self.release(current, reason="depletion_rebalance")
        try:
            replacement = self.assign(task, exclude={previous_primary})
        except Exception:
            # Fail closed: the old route is not silently restored after a depletion signal.
            self._record(
                "task.rebalance_failed",
                task_id=task.task_id,
                previous_primary=previous_primary,
            )
            raise
        self._record(
            "task.rebalanced",
            task_id=task.task_id,
            previous_primary=previous_primary,
            new_primary=replacement.primary_node,
        )
        return replacement

    def snapshot(self) -> dict[str, object]:
        return {
            "schema": ASTRAL_SCHEMA,
            "public_base": XUNIA_PUBLIC_BASE,
            "depletion_threshold": self.depletion_threshold,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "capacity": node.capacity,
                    "usage": node.usage,
                    "available": {
                        resource: node.available(resource) for resource in sorted(node.capacity)
                    },
                    "health": node.health,
                    "authorized": node.authorized,
                    "dependency_status": node.dependency_status,
                    "quarantined": node.quarantined,
                    "zone": node.zone,
                    "labels": sorted(node.labels),
                    "generation": node.generation,
                }
                for node in sorted(self.nodes.values(), key=lambda item: item.node_id)
            ],
            "active_assignments": sum(
                1 for assignment in self.assignments.values() if assignment.state == "reserved"
            ),
            "audit_events": len(self.audit),
            "audit_chain_valid": self.verify_audit_chain(),
        }


def build_grid(nodes: Iterable[ResourceNode], *, depletion_threshold: float = 0.15) -> AstralGrid:
    grid = AstralGrid(depletion_threshold=depletion_threshold)
    for node in nodes:
        grid.register(node)
    return grid


if __name__ == "__main__":
    demo = build_grid(
        [
            ResourceNode(
                "local-mac",
                capacity={"compute": 8, "memory": 16, "context": 32},
                labels={"local", "general"},
                zone="personal",
            ),
            ResourceNode(
                "nxyz-worker",
                capacity={"compute": 16, "memory": 32, "context": 64},
                labels={"cloud", "general"},
                zone="personal",
            ),
            ResourceNode(
                "zyra-runner",
                capacity={"compute": 12, "memory": 24, "context": 48},
                labels={"cloud", "general"},
                zone="personal",
            ),
        ]
    )
    job = Task(
        "demo",
        requirements={"compute": 18, "memory": 8, "context": 8},
        required_labels={"general"},
        required_zone="personal",
        shareable_resources={"compute"},
    )
    allocation = demo.assign(job)
    print(allocation)
    print(json.dumps(demo.snapshot(), indent=2))
