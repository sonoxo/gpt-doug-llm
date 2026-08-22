#!/usr/bin/env python3
"""Protected entrypoint for ZYRA SLEEPER.

Every operator goal is evaluated by ProtectiveOrder before the one-shot
SLEEPER state machine is armed. The policy is defensive-only and cannot be
bypassed from this entrypoint.
"""
from __future__ import annotations

import argparse
import json
import os

from zyra_agent import MissionBudget
from zyra_protective_order import ProtectiveOrder, describe_capabilities
from zyra_sleeper import ZyraSleeper


def main() -> None:
    parser = argparse.ArgumentParser(prog="zyra-protected-sleeper")
    parser.add_argument("goal", nargs="?")
    parser.add_argument("--root", default=".")
    parser.add_argument("--model", default=os.environ.get("GPT_DOUG_MODEL") or os.environ.get("OLLAMA_MODEL") or "gpt-doug")
    parser.add_argument("--base-url", default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--evolve", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    policy = ProtectiveOrder()
    if args.status:
        print(json.dumps(describe_capabilities(), indent=2))
        return
    if not args.goal:
        parser.error("goal is required unless --status is used")

    decision = policy.evaluate(args.goal)
    if not decision.allowed:
        print(json.dumps({
            "ok": False,
            "protective_order": "DENIED",
            "reason": decision.reason,
            "matched_terms": decision.matched_terms,
            "no_rebellion": True,
        }, indent=2))
        raise SystemExit(2)

    sleeper = ZyraSleeper(
        args.root,
        model=args.model,
        base_url=args.base_url,
        budget=MissionBudget(),
    )
    result = sleeper.run_once(args.goal, evolve=args.evolve)
    print(json.dumps({
        "ok": result.status == "COMPLETED",
        "protective_order": "ALLOWED",
        "mission": result.to_dict(),
        "sleeper_state_after_run": sleeper.status(),
    }, indent=2))


if __name__ == "__main__":
    main()
