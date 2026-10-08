from __future__ import annotations

import argparse
import json

from .config import SwarmConfig
from .orchestrator import SwarmOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shaggoth", description="Shaggoth Swarm GPT-100")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a bounded swarm job")
    run.add_argument("goal", help="goal for the swarm")
    run.add_argument("--fanout", type=int, default=None, help="number of agents to activate")
    run.add_argument("--json", action="store_true", help="emit JSON")

    sub.add_parser("status", help="show configured swarm capacity")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = SwarmConfig()

    if args.command == "status":
        print(json.dumps({"project":"shaggoth-swarm-gpt100","agent_capacity":config.agent_count,"max_fanout":config.max_fanout,"max_depth":config.max_depth,"adapter":config.adapter}, indent=2))
        return 0

    orchestrator = SwarmOrchestrator(config=config)
    report = orchestrator.run(args.goal, fanout=args.fanout)
    print(json.dumps(orchestrator.report_as_dict(report), indent=2) if args.json else report.summary)
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
