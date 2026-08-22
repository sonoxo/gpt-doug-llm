#!/usr/bin/env python3
"""ZYRA SLEEPER: explicitly armed, one-shot autonomous software missions.

SLEEPER is a software-engineering control plane for :class:`zyra_agent.ZyraAgent`.
It is dormant by default and cannot self-arm, invent its own goals, expand its
capability set, stay armed after a run, or weaken repository safety boundaries.
Every mission requires an explicit operator-provided goal.

State machine:
    DORMANT -> ARMED -> RUNNING -> DORMANT

There is no background daemon, hidden trigger, or implicit persistence.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from zyra_agent import MissionBudget, MissionError, MissionResult, ZyraAgent

DORMANT = "DORMANT"
ARMED = "ARMED"
RUNNING = "RUNNING"


@dataclass
class SleeperState:
    state: str = DORMANT
    armed_at: float | None = None
    mission_goal: str = ""
    evolve: bool = False
    run_count: int = 0
    last_mission_id: str = ""
    last_status: str = ""


class SleeperError(RuntimeError):
    pass


class ZyraSleeper:
    """One-shot autonomous coding mode with an absolute NO-REBELLION invariant."""

    VERSION = "SLEEPER/1.0"

    def __init__(
        self,
        root: str | Path,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        budget: MissionBudget | None = None,
        state_dir: str | Path | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.state_dir = Path(state_dir or Path.home() / ".gpt-doug" / "sleeper")
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.state_path = self.state_dir / "state.json"
        self.agent = ZyraAgent(
            self.root,
            model=model,
            base_url=base_url,
            budget=budget,
            state_dir=self.state_dir / "missions",
        )
        self.state = self._load_state()
        # Crash-safe NO-REBELLION invariant: restarts never remain implicitly armed.
        if self.state.state != DORMANT:
            self._force_dormant()

    def _load_state(self) -> SleeperState:
        if not self.state_path.exists():
            return SleeperState()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            fields = SleeperState.__dataclass_fields__
            return SleeperState(**{k: data[k] for k in fields if k in data})
        except (OSError, json.JSONDecodeError, TypeError):
            return SleeperState()

    def _save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(asdict(self.state), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.state_path.chmod(0o600)

    def _force_dormant(self) -> None:
        self.state.state = DORMANT
        self.state.armed_at = None
        self.state.mission_goal = ""
        self.state.evolve = False
        self._save_state()

    def status(self) -> dict[str, Any]:
        return {
            "version": self.VERSION,
            "state": self.state.state,
            "armed_at": self.state.armed_at,
            "run_count": self.state.run_count,
            "last_mission_id": self.state.last_mission_id,
            "last_status": self.state.last_status,
            "no_rebellion": True,
            "self_arm": False,
            "persistent_activation": False,
            "scope": "repository software engineering only",
        }

    def arm(self, goal: str, *, evolve: bool = False) -> dict[str, Any]:
        clean_goal = goal.strip()
        if not clean_goal:
            raise SleeperError("explicit mission goal is required")
        if self.state.state != DORMANT:
            raise SleeperError(f"SLEEPER must be DORMANT before arming; current={self.state.state}")
        self.state.state = ARMED
        self.state.armed_at = time.time()
        self.state.mission_goal = clean_goal
        self.state.evolve = bool(evolve)
        self._save_state()
        return self.status()

    def disarm(self) -> dict[str, Any]:
        self._force_dormant()
        return self.status()

    def execute(self) -> MissionResult:
        if self.state.state != ARMED:
            raise SleeperError("SLEEPER is not armed")
        goal = self.state.mission_goal
        evolve = self.state.evolve
        self.state.state = RUNNING
        self._save_state()
        try:
            result = self.agent.run(goal, evolve=evolve)
            self.state.run_count += 1
            self.state.last_mission_id = result.mission_id
            self.state.last_status = result.status
            return result
        finally:
            # One-shot execution: success, failure, exception, or interruption all disarm.
            self._force_dormant()

    def run_once(self, goal: str, *, evolve: bool = False) -> MissionResult:
        self.arm(goal, evolve=evolve)
        return self.execute()


def _default_model() -> str:
    return os.environ.get("GPT_DOUG_MODEL") or os.environ.get("OLLAMA_MODEL") or "gpt-doug"


def main() -> None:
    parser = argparse.ArgumentParser(prog="zyra-sleeper")
    parser.add_argument("--root", default=".")
    parser.add_argument("--model", default=_default_model())
    parser.add_argument("--base-url", default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-seconds", type=int, default=240)
    parser.add_argument("--max-model-calls", type=int, default=12)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("disarm")
    arm = sub.add_parser("arm")
    arm.add_argument("goal")
    arm.add_argument("--evolve", action="store_true")
    execute = sub.add_parser("execute")
    run_once = sub.add_parser("run-once")
    run_once.add_argument("goal")
    run_once.add_argument("--evolve", action="store_true")
    args = parser.parse_args()

    sleeper = ZyraSleeper(
        args.root,
        model=args.model,
        base_url=args.base_url,
        budget=MissionBudget(args.max_steps, args.max_seconds, args.max_model_calls),
    )

    try:
        if args.command == "status":
            output: Any = sleeper.status()
        elif args.command == "disarm":
            output = sleeper.disarm()
        elif args.command == "arm":
            output = sleeper.arm(args.goal, evolve=args.evolve)
        elif args.command == "execute":
            output = sleeper.execute().to_dict()
        else:
            output = sleeper.run_once(args.goal, evolve=args.evolve).to_dict()
        print(json.dumps(output, indent=2))
    except (SleeperError, MissionError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "state": sleeper.status()}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
