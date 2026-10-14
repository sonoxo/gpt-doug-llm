"""GPT-Ironman-LLM mission runner: stages work; no tools registered by default."""
from __future__ import annotations

import argparse
import json

from .stark_ironman import IronmanRuntime, StarkPlanner


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="GPT-Ironman-LLM guarded mission runtime")
    parser.add_argument("goal", nargs="+", help="Goal to stage")
    parser.add_argument("--live", action="store_true", help="Opt in to configured GPT-Doug inference")
    parser.add_argument("--model", default="default")
    args = parser.parse_args(argv)
    try:
        plan = StarkPlanner(repo_model=args.model if args.live else None).plan(" ".join(args.goal))
        report = IronmanRuntime().execute(plan)
        print(json.dumps({"stark": plan, "ironman": report}, indent=2))
    except (ValueError, RuntimeError, PermissionError) as error:
        parser.exit(2, f"GPT-Ironman staging failed: {type(error).__name__}: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())