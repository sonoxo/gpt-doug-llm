#!/usr/bin/env python3
"""Run bounded GPT-DOUG/ZYRA coding missions against an explicit local git repo.

This runner is intentionally local-first: inference goes to a local Ollama endpoint
and no Codex/OpenAI billing or quota path is used. The target repository must be
explicitly supplied by the user and remains protected by ZyraAgent's repo-scoped
file access, checkpoints, hard mission budgets, and rollback behavior.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from zyra_agent import MissionBudget, MissionError, ZyraAgent, print_agent_report
from zyra_self_heal import run_self_heal

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5-coder:7b"


def resolve_repo(raw: str) -> Path:
    """Resolve an explicit path to the root of a local git working tree."""
    requested = Path(raw).expanduser().resolve()
    if not requested.is_dir():
        raise ValueError(f"repository directory does not exist: {requested}")
    proc = subprocess.run(
        ["git", "-C", str(requested), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise ValueError(f"not a git repository: {requested}")
    root = Path(proc.stdout.strip()).resolve()
    if not root.is_dir():
        raise ValueError("git returned an invalid repository root")
    return root


def installed_models(base_url: str) -> list[str]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/tags",
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode())
    return [item.get("name", "") for item in payload.get("models", []) if item.get("name")]


def choose_model(models: list[str], requested: str) -> str:
    if not models:
        raise RuntimeError("no local Ollama models are installed")
    candidates = [
        requested,
        os.environ.get("ZYRA_MODEL", ""),
        os.environ.get("OLLAMA_MODEL", ""),
        DEFAULT_MODEL,
        "gpt-doug",
        "qwen2.5-coder",
        "qwen2.5",
        "llama3",
    ]
    for wanted in candidates:
        if not wanted:
            continue
        for name in models:
            if name == wanted or name.startswith(wanted + ":"):
                return name
    return models[0]


class LocalRepoAgent(ZyraAgent):
    """ZyraAgent with a deterministic Node/TypeScript final verification gate."""

    def _node_final_gate(self) -> dict[str, object]:
        checks = [
            ("typescript", ["npm", "run", "check", "--if-present"], 180),
            ("tests", ["npm", "run", "test", "--if-present"], 240),
            ("build", ["npm", "run", "build", "--if-present"], 300),
            ("diff", ["git", "diff", "--check"], 60),
        ]
        reports: list[dict[str, object]] = []
        for label, args, timeout in checks:
            result = self._run_process(args, timeout=timeout)
            reports.append({"name": label, **result})
            if not result.get("ok"):
                return {
                    "check": "syntax",
                    "ok": False,
                    "returncode": result.get("returncode", 1),
                    "output": f"{label} failed\n{result.get('output', '')}",
                    "subchecks": reports,
                }
        return {
            "check": "syntax",
            "ok": True,
            "returncode": 0,
            "output": "TypeScript/tests/build/diff gates passed",
            "subchecks": reports,
        }

    def _tool_run_check(self, check: str, touched: list[str]) -> dict[str, object]:
        if check == "syntax" and (self.root / "package.json").exists():
            return self._node_final_gate()
        return super()._tool_run_check(check, touched)


def bootstrap_repo(root: Path) -> None:
    """Install declared Node dependencies only when explicitly requested."""
    if not (root / "package.json").exists():
        return
    command = ["npm", "ci"] if (root / "package-lock.json").exists() else ["npm", "install"]
    proc = subprocess.run(command, cwd=str(root), timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"dependency bootstrap failed with exit code {proc.returncode}")


def read_goal(args: argparse.Namespace) -> str:
    if args.goal:
        return args.goal.strip()
    if args.goal_file:
        path = Path(args.goal_file).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"goal file does not exist: {path}")
        return path.read_text(encoding="utf-8").strip()
    raise ValueError("provide --goal or --goal-file")


def bounded(value: int, low: int, high: int, label: str) -> int:
    if value < low or value > high:
        raise ValueError(f"{label} must be between {low} and {high}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a bounded local ZYRA coding mission against an explicit git repo without Codex credits."
    )
    parser.add_argument("--repo", required=True, help="Target local git repository path")
    goal_group = parser.add_mutually_exclusive_group(required=True)
    goal_group.add_argument("--goal", help="Mission goal text")
    goal_group.add_argument("--goal-file", help="UTF-8 file containing the mission goal")
    parser.add_argument("--model", default=os.environ.get("ZYRA_MODEL", DEFAULT_MODEL))
    parser.add_argument("--base-url", default=os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--max-steps", type=int, default=24)
    parser.add_argument("--max-seconds", type=int, default=1800)
    parser.add_argument("--max-model-calls", type=int, default=36)
    parser.add_argument("--bootstrap", action="store_true", help="Run npm ci/install before the mission when package.json exists")
    parser.add_argument("--plan", action="store_true", help="Preview a plan without writing files")
    args = parser.parse_args()

    try:
        root = resolve_repo(args.repo)
        goal = read_goal(args)
        if not goal:
            raise ValueError("mission goal is empty")

        max_steps = bounded(args.max_steps, 1, 64, "max steps")
        max_seconds = bounded(args.max_seconds, 30, 7200, "max seconds")
        max_model_calls = bounded(args.max_model_calls, 1, 96, "max model calls")

        print("🟣 GPT-DOUG LOCAL REPO AGENT")
        print(f"📂 Target: {root}")
        print("💳 Codex/OpenAI credits: NOT USED")
        print("🧠 Provider: local Ollama")

        if args.bootstrap:
            print("📦 Bootstrapping declared dependencies…")
            bootstrap_repo(root)

        heal = run_self_heal(start_ollama=True, persist=True)
        if not heal.get("healthy"):
            raise RuntimeError("local model runtime is not healthy after one self-heal pass")

        model = choose_model(installed_models(args.base_url), args.model)
        print(f"🤖 Model: {model}")

        budget = MissionBudget(
            max_steps=max_steps,
            max_seconds=max_seconds,
            max_model_calls=max_model_calls,
        )
        agent = LocalRepoAgent(root, model=model, base_url=args.base_url, budget=budget)

        if args.plan:
            print("\n🧭 PLAN")
            print(agent.preview(goal, evolve=False))
            return 0

        result = agent.run(goal, evolve=False)
        print_agent_report(result)
        return 0 if result.status == "PASS" else 1

    except (ValueError, RuntimeError, MissionError, OSError) as exc:
        print(f"❌ LOCAL REPO AGENT ERROR // {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
