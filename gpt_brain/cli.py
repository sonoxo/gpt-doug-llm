from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .kernel import BrainKernel
from .memory import BrainMemory
from .status import build_status
from warhawk import WarHawkSwarm


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPT-Doug ontology-first brain kernel")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="run an ontology-first multi-agent task")
    run.add_argument("task", nargs="+", help="task text")
    run.add_argument("--json", action="store_true", dest="as_json")

    clone = sub.add_parser("ingest-clone", help="seed behavioral memory from a transcript/export")
    clone.add_argument("path", help="path to a text transcript/export")
    clone.add_argument("--provenance", default="user-authorized-transcript")

    recall = sub.add_parser("recall", help="inspect recalled brain memory")
    recall.add_argument("query", nargs="+")
    recall.add_argument("--limit", type=int, default=8)

    sub.add_parser("status", help="show brain readiness without running a model")
    sub.add_parser("doctor", help="show detailed readiness diagnostics")

    warhawk = sub.add_parser(
        "warhawk",
        help="US-01-GoDsWarHawk bounded defensive software swarm",
    )
    warhawk_sub = warhawk.add_subparsers(dest="warhawk_command", required=True)

    warhawk_status = warhawk_sub.add_parser("status", help="show swarm profile and policy gates")
    warhawk_status.add_argument("--repo", default=".")
    warhawk_status.add_argument("--workers", type=int, default=6)

    warhawk_plan = warhawk_sub.add_parser("plan", help="build a dry-run swarm mission plan")
    warhawk_plan.add_argument("mission", nargs="+")
    warhawk_plan.add_argument("--repo", default=".")
    warhawk_plan.add_argument("--workers", type=int, default=6)

    warhawk_run = warhawk_sub.add_parser("run", help="run bounded software workers")
    warhawk_run.add_argument("mission", nargs="+")
    warhawk_run.add_argument("--repo", default=".")
    warhawk_run.add_argument("--workers", type=int, default=6)
    warhawk_run.add_argument("--execute", action="store_true")
    return parser


def _error(kind: str, message: str) -> int:
    print(
        json.dumps(
            {"ok": False, "error": kind, "message": message},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 2


def _run_warhawk(args: argparse.Namespace) -> int:
    swarm = WarHawkSwarm(root=args.repo, max_workers=args.workers)
    try:
        if args.warhawk_command == "status":
            payload = swarm.status()
        elif args.warhawk_command == "plan":
            payload = swarm.plan(" ".join(args.mission))
        else:
            payload = swarm.run(" ".join(args.mission), execute=args.execute)
    except (PermissionError, ValueError) as exc:
        return _error("warhawk_run_failed", str(exc))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "warhawk":
        return _run_warhawk(args)

    memory = BrainMemory()

    if args.command in {None, "status", "doctor"}:
        payload = build_status()
        if args.command == "doctor":
            payload["doctor"] = {
                "core": "PASS" if payload["readiness"]["core_ready"] else "FAIL",
                "model": "PASS" if payload["readiness"]["model_ready"] else "NOT_READY",
                "note": (
                    "Core status does not require a configured model. "
                    "Model tasks require provider/model readiness."
                ),
            }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "ingest-clone":
        path = Path(args.path)
        if not path.is_file():
            return _error("input_not_found", f"transcript file not found: {path}")
        try:
            count = memory.ingest_transcript(
                path.read_text(encoding="utf-8"),
                provenance=args.provenance,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            return _error("clone_ingest_failed", type(exc).__name__)
        print(json.dumps({"ok": True, "ingested": count, "source": str(path)}, indent=2))
        return 0

    if args.command == "recall":
        if args.limit < 1:
            return _error("invalid_limit", "recall limit must be at least 1")
        print(
            json.dumps(
                memory.recall(" ".join(args.query), args.limit),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    try:
        result = BrainKernel(memory=memory).run(" ".join(args.task))
    except (OSError, RuntimeError, ValueError) as exc:
        return _error("brain_run_failed", str(exc))

    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
