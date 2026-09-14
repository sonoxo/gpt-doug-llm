"""GPT-DOUG Astral Grid: governed, resource-aware software task routing.

This module models software compute/resource orchestration only. It does not control
vehicles, weapons, physical power transfer, or other real-world actuation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


XUNIA_PUBLIC_BASE = "https://xunia.org"


@dataclass(slots=True)
class ResourceNode:
    node_id: str
    capacity: float
    load: float = 0.0
    health: float = 1.0
    authorized: bool = True
    labels: set[str] = field(default_factory=set)

    @property
    def available(self) -> float:
        return max(0.0, self.capacity - self.load)

    @property
    def healthy(self) -> bool:
        return self.health >= 0.5


@dataclass(slots=True)
class Task:
    task_id: str
    required_capacity: float
    priority: int = 50
    required_labels: set[str] = field(default_factory=set)


@dataclass(slots=True)
class Assignment:
    task_id: str
    primary_node: str
    helper_nodes: list[str]
    reserved_capacity: float
    score: float


class AstralGrid:
    """Small fail-closed reference scheduler with auditable routing decisions."""

    def __init__(self) -> None:
        self.nodes: dict[str, ResourceNode] = {}
        self.audit: list[dict[str, object]] = []

    def _record(self, event: str, **payload: object) -> None:
        self.audit.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event,
                **payload,
            }
        )

    def register(self, node: ResourceNode) -> None:
        if node.capacity <= 0:
            raise ValueError("node capacity must be positive")
        self.nodes[node.node_id] = node
        self._record(
            "node.registered",
            node_id=node.node_id,
            capacity=node.capacity,
            labels=sorted(node.labels),
        )

    def update_node(
        self,
        node_id: str,
        *,
        load: float | None = None,
        health: float | None = None,
        authorized: bool | None = None,
    ) -> None:
        node = self.nodes[node_id]
        if load is not None:
            node.load = min(max(load, 0.0), node.capacity)
        if health is not None:
            node.health = min(max(health, 0.0), 1.0)
        if authorized is not None:
            node.authorized = authorized
        self._record(
            "node.updated",
            node_id=node_id,
            load=node.load,
            health=node.health,
            authorized=node.authorized,
        )

    def _eligible(self, task: Task) -> list[ResourceNode]:
        return [
            node
            for node in self.nodes.values()
            if node.authorized
            and node.healthy
            and task.required_labels.issubset(node.labels)
            and node.available > 0
        ]

    @staticmethod
    def _score(node: ResourceNode, task: Task) -> float:
        capacity_ratio = min(node.available / max(task.required_capacity, 0.0001), 2.0)
        load_ratio = node.load / node.capacity
        priority_weight = min(max(task.priority, 0), 100) / 100
        return (
            node.health * 0.45
            + capacity_ratio * 0.35
            + (1.0 - load_ratio) * 0.15
            + priority_weight * 0.05
        )

    def assign(self, task: Task, *, allow_peer_assist: bool = True) -> Assignment:
        if task.required_capacity <= 0:
            raise ValueError("task.required_capacity must be positive")

        eligible = sorted(
            self._eligible(task),
            key=lambda node: self._score(node, task),
            reverse=True,
        )

        if not eligible:
            self._record("task.rejected", task_id=task.task_id, reason="no_eligible_nodes")
            raise RuntimeError("No healthy authorized Astral node can accept this task")

        primary = eligible[0]
        helpers: list[ResourceNode] = []
        remaining = max(0.0, task.required_capacity - primary.available)

        if remaining > 0 and allow_peer_assist:
            for candidate in eligible[1:]:
                helpers.append(candidate)
                remaining -= candidate.available
                if remaining <= 0:
                    break

        if remaining > 0:
            self._record(
                "task.rejected",
                task_id=task.task_id,
                reason="insufficient_capacity",
                requested=task.required_capacity,
            )
            raise RuntimeError("Insufficient authorized capacity for this task")

        participants = [primary, *helpers]
        reserve_left = task.required_capacity
        for node in participants:
            delta = min(node.available, reserve_left)
            node.load += delta
            reserve_left -= delta
            if reserve_left <= 0:
                break

        assignment = Assignment(
            task_id=task.task_id,
            primary_node=primary.node_id,
            helper_nodes=[node.node_id for node in helpers],
            reserved_capacity=task.required_capacity,
            score=self._score(primary, task),
        )
        self._record(
            "task.assigned",
            task_id=task.task_id,
            primary_node=assignment.primary_node,
            helper_nodes=assignment.helper_nodes,
            reserved_capacity=assignment.reserved_capacity,
            score=round(assignment.score, 5),
        )
        return assignment

    def release(self, assignment: Assignment) -> None:
        participant_ids = [assignment.primary_node, *assignment.helper_nodes]
        reserve_left = assignment.reserved_capacity
        for node_id in participant_ids:
            node = self.nodes.get(node_id)
            if node is None:
                continue
            delta = min(node.load, reserve_left)
            node.load -= delta
            reserve_left -= delta
            if reserve_left <= 0:
                break
        self._record("task.released", task_id=assignment.task_id)

    def snapshot(self) -> dict[str, object]:
        return {
            "public_base": XUNIA_PUBLIC_BASE,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "capacity": node.capacity,
                    "load": node.load,
                    "available": node.available,
                    "health": node.health,
                    "authorized": node.authorized,
                    "labels": sorted(node.labels),
                }
                for node in sorted(self.nodes.values(), key=lambda item: item.node_id)
            ],
            "audit_events": len(self.audit),
        }


def build_grid(nodes: Iterable[ResourceNode]) -> AstralGrid:
    grid = AstralGrid()
    for node in nodes:
        grid.register(node)
    return grid


if __name__ == "__main__":
    demo = build_grid(
        [
            ResourceNode("local-mac", capacity=8, labels={"local", "cpu"}),
            ResourceNode("nxyz-worker", capacity=16, labels={"cloud", "cpu"}),
            ResourceNode("zyra-runner", capacity=12, labels={"cloud", "cpu"}),
        ]
    )
    job = Task("demo", required_capacity=18, required_labels={"cpu"})
    allocation = demo.assign(job)
    print(allocation)
    print(demo.snapshot())
