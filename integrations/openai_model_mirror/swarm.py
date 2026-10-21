"""Bounded, read-only logical agent fleet backed by one OpenAI model identity.

REA is optionally used to inspect an approved local model through the existing
mirror integration. This is not weight cloning, inference, remote deployment,
or autonomous self-propagation. No network, threads or subprocesses are used by
virtual fleet planning unless the operator explicitly requests REA inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .mirror import DEFAULT_ROOT, MirrorError, inspect_with_rea, valid_repo

SCHEMA = "gpt-doug.rea-virtual-swarm.v1"
MAX_VIRTUAL_AGENTS = 99_999_999
MAX_SLOTS = 64
MAX_SAMPLE = 64
DEFAULT_ROLES = (
    "ontology-reviewer",
    "provenance-auditor",
    "policy-checker",
    "model-catalog-reviewer",
    "local-analysis-planner",
    "integrity-verifier",
)


def _digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _positive(name: str, value: int, maximum: int, minimum: int = 1) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise MirrorError(f"{name} must be an integer from {minimum} to {maximum}")
    return value


def shard_partition(total: int, slots: int) -> list[dict[str, int]]:
    """Exactly partition a huge logical keyspace into at most 64 worker slots."""
    _positive("count", total, MAX_VIRTUAL_AGENTS)
    _positive("slots", slots, MAX_SLOTS)
    base, extra = divmod(total, slots)
    return [
        {
            "slot": slot,
            "first_zero_based_id": slot if slot < total else -1,
            "stride": slots,
            "agent_count": base + (1 if slot < extra else 0),
        }
        for slot in range(slots)
    ]


def _sample_ids(total: int, sample: int) -> list[int]:
    if sample == 0:
        return []
    if sample == 1:
        return [0]
    if total <= sample:
        return list(range(total))
    return [(index * (total - 1)) // (sample - 1) for index in range(sample)]


def create_plan(
    *,
    model: str = "openai/gpt-oss-20b",
    count: int = MAX_VIRTUAL_AGENTS,
    slots: int = 8,
    sample: int = 12,
    rea_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    model = valid_repo(model)
    _positive("count", count, MAX_VIRTUAL_AGENTS)
    _positive("slots", slots, MAX_SLOTS)
    _positive("sample", sample, MAX_SAMPLE, minimum=0)
    if rea_analysis is not None:
        if not isinstance(rea_analysis, dict) or rea_analysis.get("model") != model or rea_analysis.get("status") != "rea-static-inspection":
            raise MirrorError("REA inspection must be successful and match the model")
        rea_digest = _digest(rea_analysis)
        rea_status = "inspected-local-model"
    else:
        rea_digest = None
        rea_status = "not-run; model weights are not verified"
    identity = {
        "schema": SCHEMA,
        "model": model,
        "virtual_count": count,
        "slots": slots,
        "rea_evidence_sha256": rea_digest,
    }
    pool_id = _digest(identity)
    partitions = shard_partition(count, slots)
    samples = [
        {
            "agent_id": f"DOUG-{index + 1:08d}",
            "zero_based_index": index,
            "role": DEFAULT_ROLES[index % len(DEFAULT_ROLES)],
            "slot": index % slots,
            "status": "virtual-not-running",
        }
        for index in _sample_ids(count, sample)
    ]
    return {
        "schema": SCHEMA,
        "status": "logical-fleet-plan-only",
        "pool_id": pool_id,
        "model": model,
        "rea_inspection_status": rea_status,
        "rea_evidence_sha256": rea_digest,
        "requested_virtual_agents": count,
        "indexed_virtual_agents": count,
        "concurrent_slot_limit": slots,
        "active_processes_started": 0,
        "weights_copied": 0,
        "agents_executing_inference": 0,
        "memory_complexity": "O(slots + sample); no per-agent allocation",
        "partitions": partitions,
        "sample": samples,
        "external_network_access": False,
        "satellite_uplink": False,
        "self_propagation": False,
        "remote_deployment": False,
        "requires_operator_approval_for_real_compute": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Project up to 99,999,999 GPT-Doug logical agents without spawning processes"
    )
    parser.add_argument("--model", default="openai/gpt-oss-20b", help="Official OpenAI model repository ID")
    parser.add_argument("--count", type=int, default=MAX_VIRTUAL_AGENTS)
    parser.add_argument("--slots", type=int, default=8, help="Logical work partitions (1..64)")
    parser.add_argument("--sample", type=int, default=12, help="Preview up to 64 virtual identities")
    parser.add_argument("--inspect-rea", action="store_true", help="Run REA on already-mirrored local weights; no downloads")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Approved local model cache for REA inspection")
    parser.add_argument("--output", type=Path, help="Optional new local JSON manifest file (never overwrites)")
    args = parser.parse_args(argv)
    try:
        inspection = inspect_with_rea(args.root, args.model, max_files=16) if args.inspect_rea else None
        result = create_plan(
            model=args.model,
            count=args.count,
            slots=args.slots,
            sample=args.sample,
            rea_analysis=inspection,
        )
    except (MirrorError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2
    if args.output is not None:
        path = args.output.expanduser()
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write("\n")
        except OSError as exc:
            print(json.dumps({"status": "blocked", "error": f"cannot create new local manifest: {exc}"}), file=sys.stderr)
            return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
