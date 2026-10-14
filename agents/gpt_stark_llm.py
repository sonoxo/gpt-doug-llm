"""GPT-Stark-LLM architect command: source-grounded planning only."""
from __future__ import annotations

import argparse
import json

from .stark_ironman import StarkPlanner


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GPT-Stark-LLM planning role")
    parser.add_argument("goal", nargs="+", help="Goal to plan")
    parser.add_argument("--live", action="store_true", help="Opt in to the configured GPT-Doug model")
    parser.add_argument("--model", default="default", help="Optional configured model ID")
    args = parser.parse_args(argv)
    try:
        planner = StarkPlanner(repo_model=args.model if args.live else None)
        print(json.dumps(planner.plan(" ".join(args.goal)), indent=2))
    except (ValueError, RuntimeError, PermissionError) as error:
        parser.exit(2, f"GPT-Stark planning failed: {type(error).__name__}: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())