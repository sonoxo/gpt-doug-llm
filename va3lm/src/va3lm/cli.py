from __future__ import annotations

import argparse
import json

from va3lm.agent_runtime import run_coding_agent
from va3lm.agents import roster
from va3lm.brain import ask
from va3lm.capabilities import capability_manifest
from va3lm.explainer import explain
from va3lm.federal_intel import (
    federal_intel_entity,
    federal_intel_manifest,
    verified_github_sources,
)
from va3lm.max_memory import memory_manager
from va3lm.ontology import schema
from va3lm.planner import build_plan
from va3lm.tracking import sample_track, to_geojson, tracking_manifest
from va3lm.workspace import WorkspaceRuntime


def _dump(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(prog="va3lm")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("agents")
    sub.add_parser("ontology")
    sub.add_parser("capabilities")

    tracking = sub.add_parser("tracking")
    tracking.add_argument("--sample", action="store_true", help="emit deterministic Virginia demo GeoJSON")

    federal_intel = sub.add_parser("federal-intel")
    federal_filter = federal_intel.add_mutually_exclusive_group()
    federal_filter.add_argument("--entity", choices=["cia", "nsa", "nro", "ngp", "gdip"])
    federal_filter.add_argument("--github-only", action="store_true", help="emit verified official GitHub sources only")

    plan = sub.add_parser("plan")
    plan.add_argument("goal")

    brain = sub.add_parser("brain")
    brain.add_argument("prompt")
    brain.add_argument("--session", default="terminal", help="bounded MAX memory session id")

    memory = sub.add_parser("memory")
    memory.add_argument("--session", default="terminal", help="bounded MAX memory session id")
    memory.add_argument("--query", default="", help="rank compact memory around this query")
    memory.add_argument("--clear", action="store_true", help="clear the selected in-process memory session")

    exp = sub.add_parser("explain")
    exp.add_argument("subject")

    workspace = sub.add_parser("workspace")
    workspace.add_argument("--root", default=None, help="workspace root; defaults to VA3LM_WORKSPACE_ROOT or current directory")

    execute = sub.add_parser("execute")
    execute.add_argument("goal")
    execute.add_argument("--workspace", default=None, help="workspace root; defaults to VA3LM_WORKSPACE_ROOT or current directory")
    execute.add_argument("--approve", action="store_true", help="explicitly approve workspace mutations and allow-listed commands")
    execute.add_argument("--max-rounds", type=int, default=4, help="bounded model/tool rounds (1-8)")

    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8088)

    args = parser.parse_args()
    if args.command == "agents":
        _dump(roster())
    elif args.command == "ontology":
        _dump(schema())
    elif args.command == "capabilities":
        _dump(capability_manifest())
    elif args.command == "tracking":
        _dump(to_geojson(sample_track()) if args.sample else tracking_manifest())
    elif args.command == "federal-intel":
        if args.github_only:
            _dump({"mode": "VERIFIED_OFFICIAL_GITHUB_ONLY", "sources": verified_github_sources()})
        elif args.entity:
            _dump(federal_intel_entity(args.entity))
        else:
            _dump(federal_intel_manifest())
    elif args.command == "plan":
        _dump(build_plan(args.goal))
    elif args.command == "brain":
        _dump(ask(args.prompt, args.session))
    elif args.command == "memory":
        if args.clear:
            _dump({"sessionId": args.session, "cleared": memory_manager.clear(args.session)})
        else:
            _dump(memory_manager.get(args.session).snapshot(args.query))
    elif args.command == "explain":
        _dump(explain(args.subject))
    elif args.command == "workspace":
        runtime = WorkspaceRuntime(args.root)
        _dump({"runtime": runtime.status(), "project": runtime.inspect_project()})
    elif args.command == "execute":
        _dump(
            run_coding_agent(
                args.goal,
                workspace=args.workspace,
                approved=args.approve,
                max_rounds=args.max_rounds,
            )
        )
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("va3lm.app:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
