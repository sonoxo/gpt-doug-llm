from __future__ import annotations

import argparse
import json

from va3lm.agents import roster
from va3lm.brain import ask
from va3lm.capabilities import capability_manifest
from va3lm.explainer import explain
from va3lm.ontology import schema
from va3lm.planner import build_plan
from va3lm.tracking import sample_track, to_geojson, tracking_manifest


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

    plan = sub.add_parser("plan")
    plan.add_argument("goal")

    brain = sub.add_parser("brain")
    brain.add_argument("prompt")

    exp = sub.add_parser("explain")
    exp.add_argument("subject")

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
    elif args.command == "plan":
        _dump(build_plan(args.goal))
    elif args.command == "brain":
        _dump(ask(args.prompt))
    elif args.command == "explain":
        _dump(explain(args.subject))
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("va3lm.app:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
