"""Bounded recursive planning and metadata-only credential rotation planning.

This module never launches a worker fleet or changes provider credentials.
It produces inspectable plans for operator review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

Decomposer = Callable[[str], Iterable[str]]
_SECRET_FIELD = re.compile(r"(?:secret|token|password|private.?key|credential.?value|api.?key)", re.I)


@dataclass
class PlanNode:
    node_id: str
    goal: str
    depth: int
    status: str = "PLANNED"
    children: list["PlanNode"] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["children"] = [child.to_dict() for child in self.children]
        return result


@dataclass
class PlanResult:
    root: PlanNode
    node_count: int
    max_depth: int
    budget_exhausted: bool
    skipped_cycles: int

    def to_dict(self) -> dict:
        return {
            "schema": "gpt-doug/recursive-plan/v1",
            "root": self.root.to_dict(),
            "node_count": self.node_count,
            "max_depth": self.max_depth,
            "budget_exhausted": self.budget_exhausted,
            "skipped_cycles": self.skipped_cycles,
        }


def _normalise(value: str) -> str:
    return " ".join(value.casefold().split())


def _node_id(path: Sequence[str]) -> str:
    seed = "/".join(_normalise(part) for part in path)
    return "plan-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def default_decomposer(goal: str) -> list[str]:
    """Return bounded, auditable workstreams; no model or network is called."""
    text = _normalise(goal)
    if text.startswith(("[step]", "[workstream]", "[plan]", "[build]", "[verify]", "[review]")):
        return []
    if any(term in text for term in ("rotate", "credential", "secret", "api key", "universal key")):
        return [
            "[STEP] Inventory credential metadata from approved registries; never read secret values",
            "[STEP] Confirm ownership, provider, environment, consumers, dependencies, and criticality",
            "[STEP] Draft a canary-first provider rotation batch with explicit operator approval",
            "[STEP] Issue replacement credentials through each provider's authorized interface",
            "[STEP] Validate replacements and migrate one consumer at a time with rollback checkpoints",
            "[STEP] Revoke old credentials only after health checks pass and an operator approves",
            "[STEP] Record redacted evidence, failures, rollback status, and follow-up work",
        ]
    if any(term in text for term in ("fleet", "swarm", "clone", "scale", "worker")):
        return [
            "[WORKSTREAM] Define virtual identity namespace separately from active worker capacity",
            "[WORKSTREAM] Partition work into idempotent jobs with bounded retries and explicit ownership",
            "[WORKSTREAM] Set provider-aware concurrency, rate limits, budgets, and backpressure",
            "[WORKSTREAM] Add health checks, telemetry, checkpointing, cancellation, and rollback",
            "[WORKSTREAM] Run synthetic load tests before any operator-approved deployment",
            "[WORKSTREAM] Publish an evidence-backed capability brief with limitations clearly stated",
        ]
    if any(term in text for term in ("announce", "publish", "world", "public brief")):
        return [
            "[WORKSTREAM] State implemented capabilities and link to verifiable repository evidence",
            "[WORKSTREAM] Separate tested functionality from plans, simulations, and aspirational scale",
            "[WORKSTREAM] Redact credentials, private data, and unsupported affiliations or performance claims",
            "[WORKSTREAM] Prepare a public draft for human review; do not broadcast automatically",
        ]
    return [
        "[PLAN] Define a measurable objective and scope",
        "[BUILD] Implement the smallest reversible increment",
        "[VERIFY] Run focused tests, security checks, and evidence validation",
        "[REVIEW] Inspect results and decide whether another bounded cycle is justified",
    ]


class RecursivePlanner:
    """Depth-first planner with hard node/depth budgets and cycle detection."""

    def __init__(self, decomposer: Decomposer = default_decomposer, *, max_depth: int = 4, max_nodes: int = 64):
        if max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if max_nodes < 1:
            raise ValueError("max_nodes must be >= 1")
        self.decomposer = decomposer
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def plan(self, goal: str) -> PlanResult:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("goal must be a non-empty string")
        budget = {"nodes": 0, "exhausted": False, "cycles": 0}

        def visit(current: str, depth: int, ancestors: frozenset[str], path: tuple[str, ...]) -> PlanNode | None:
            if budget["nodes"] >= self.max_nodes:
                budget["exhausted"] = True
                return None
            budget["nodes"] += 1
            node = PlanNode(node_id=_node_id(path + (current,)), goal=current.strip(), depth=depth)
            key = _normalise(current)
            if depth >= self.max_depth:
                node.notes.append("Depth budget reached; no further decomposition performed.")
                if list(self.decomposer(current)):
                    budget["exhausted"] = True
                return node

            child_goals = list(self.decomposer(current))
            if any(not isinstance(child, str) or not child.strip() for child in child_goals):
                raise ValueError("decomposer must return non-empty strings")
            seen_siblings: set[str] = set()
            for child in child_goals:
                child_key = _normalise(child)
                if child_key in ancestors or child_key == key or child_key in seen_siblings:
                    budget["cycles"] += 1
                    node.notes.append("Repeated/cyclic subgoal skipped.")
                    continue
                seen_siblings.add(child_key)
                if budget["nodes"] >= self.max_nodes:
                    budget["exhausted"] = True
                    node.notes.append("Node budget reached; remaining subgoals were not expanded.")
                    break
                expanded = visit(child, depth + 1, ancestors | {key}, path + (current,))
                if expanded is not None:
                    node.children.append(expanded)
            return node

        root = visit(goal.strip(), 0, frozenset(), ())
        assert root is not None
        return PlanResult(root, budget["nodes"], self.max_depth, budget["exhausted"], budget["cycles"])


def _reject_secret_values(value, path: str = "$") -> None:
    """Reject secret-bearing field names before rotation metadata is serialized."""
    if isinstance(value, dict):
        for key, child in value.items():
            if _SECRET_FIELD.search(str(key)):
                raise ValueError(f"secret-like field name is not allowed at {path}.{key}")
            _reject_secret_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_values(child, f"{path}[{index}]")


def build_rotation_plan(records: list[dict], *, batch_size: int = 5) -> dict:
    """Build a dry-run plan for explicitly requested, owner-confirmed metadata.

    It never generates, reads, sends, or revokes a credential. An actual
    provider rotation must be performed through its authorized control plane.
    """
    if not isinstance(records, list):
        raise ValueError("credential metadata must be a JSON list")
    if batch_size < 1 or batch_size > 100:
        raise ValueError("batch_size must be between 1 and 100")

    candidates: list[dict] = []
    held: list[dict] = []
    identifiers: set[str] = set()
    required = {"credential_id", "provider", "alias", "environment"}
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        _reject_secret_values(record)
        missing = required - record.keys()
        if missing:
            raise ValueError(f"record {index} missing metadata: {', '.join(sorted(missing))}")
        credential_id = str(record["credential_id"]).strip()
        if not credential_id or credential_id in identifiers:
            raise ValueError(f"record {index} has an empty or duplicate credential_id")
        identifiers.add(credential_id)
        safe_record = {
            "credential_id": credential_id,
            "provider": str(record["provider"]),
            "alias": str(record["alias"]),
            "environment": str(record["environment"]),
            "owner_confirmed": record.get("owner_confirmed") is True,
            "rotation_requested": record.get("rotation_requested") is True,
            "consumers": list(record.get("consumers", [])) if isinstance(record.get("consumers", []), list) else [],
        }
        if safe_record["owner_confirmed"] and safe_record["rotation_requested"]:
            candidates.append(safe_record)
        else:
            safe_record["hold_reason"] = "requires explicit rotation request and owner confirmation"
            held.append(safe_record)

    batches = []
    for offset in range(0, len(candidates), batch_size):
        batch_records = candidates[offset:offset + batch_size]
        batches.append({
            "batch": len(batches) + 1,
            "mode": "DRY_RUN_ONLY",
            "credential_ids": [item["credential_id"] for item in batch_records],
            "steps": [
                "operator reviews provider, owner, environment, consumers, and dependency graph",
                "authorized operator issues replacement through provider control plane",
                "validate new credential with a non-destructive health check",
                "migrate consumers one at a time and verify service health",
                "revoke old credential only after successful migration and separate approval",
                "append redacted evidence and rollback outcome to audit record",
            ],
        })
    return {
        "schema": "gpt-doug/credential-rotation-plan/v1",
        "mode": "DRY_RUN_ONLY",
        "secret_values_processed": False,
        "provider_mutations_performed": False,
        "candidate_count": len(candidates),
        "held_count": len(held),
        "batch_size": batch_size,
        "batches": batches,
        "held": held,
        "notice": "This plan does not rotate credentials. Perform and verify every change through the authorized provider interface.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan_cmd = sub.add_parser("plan", help="create a bounded recursive mission plan")
    plan_cmd.add_argument("goal")
    plan_cmd.add_argument("--max-depth", type=int, default=4)
    plan_cmd.add_argument("--max-nodes", type=int, default=64)
    rotate_cmd = sub.add_parser("rotation-plan", help="create a metadata-only dry-run key rotation plan")
    rotate_cmd.add_argument("--input", type=Path, required=True, help="JSON list of credential metadata, not secret values")
    rotate_cmd.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = RecursivePlanner(max_depth=args.max_depth, max_nodes=args.max_nodes).plan(args.goal)
            print(json.dumps(result.to_dict(), indent=2))
        else:
            records = json.loads(args.input.read_text(encoding="utf-8"))
            print(json.dumps(build_rotation_plan(records, batch_size=args.batch_size), indent=2))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
