from __future__ import annotations

import argparse
import json
from pathlib import Path

from .kernel import BrainKernel
from .memory import BrainMemory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPT-Doug ontology-first brain kernel")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run an ontology-first multi-agent task")
    run.add_argument("task", nargs="+", help="task text")
    run.add_argument("--json", action="store_true", dest="as_json")

    clone = sub.add_parser("ingest-clone", help="seed behavioral memory from a transcript/export")
    clone.add_argument("path", help="path to a text transcript/export")
    clone.add_argument("--provenance", default="user-authorized-transcript")

    recall = sub.add_parser("recall", help="inspect recalled brain memory")
    recall.add_argument("query", nargs="+")
    recall.add_argument("--limit", type=int, default=8)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    memory = BrainMemory()
    if args.command == "ingest-clone":
        path = Path(args.path)
        count = memory.ingest_transcript(
            path.read_text(encoding="utf-8"),
            provenance=args.provenance,
        )
        print(json.dumps({"ingested": count, "source": str(path)}, indent=2))
        return 0
    if args.command == "recall":
        print(
            json.dumps(
                memory.recall(" ".join(args.query), args.limit),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    result = BrainKernel(memory=memory).run(" ".join(args.task))
    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
