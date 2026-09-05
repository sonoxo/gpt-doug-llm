#!/usr/bin/env python3
"""Cyber CPR: local-first defensive repository heartbeat and bounded remediation CLI."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".cyber-cpr"
STATE_FILE = STATE_DIR / "state.json"
DEFAULT_INTERVAL = 180
STREAK_TARGET = 5


@dataclass
class RepoPulse:
    repo: str
    state: str
    details: str
    failed_runs: list[dict[str, Any]]
    pending_runs: list[dict[str, Any]]


def _run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def ensure_prerequisites() -> None:
    if shutil.which("gh") is None:
        raise SystemExit("Cyber CPR requires the GitHub CLI (`gh`).")
    auth = _run(["gh", "auth", "status"])
    if auth.returncode != 0:
        raise SystemExit("GitHub CLI is not authenticated. Run `gh auth login` first.")


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"repos": {}}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"repos": {}}


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    tmp.replace(STATE_FILE)


def fetch_recent_runs(repo: str, limit: int = 20) -> list[dict[str, Any]]:
    result = _run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--limit",
            str(limit),
            "--json",
            "databaseId,name,status,conclusion,workflowName,headSha,createdAt,url",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Unable to inspect {repo}")
    return json.loads(result.stdout or "[]")


def latest_per_workflow(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        key = str(run.get("workflowName") or run.get("name") or "unknown")
        if key not in latest:
            latest[key] = run
    return list(latest.values())


def pulse_repo(repo: str) -> RepoPulse:
    runs = latest_per_workflow(fetch_recent_runs(repo))
    failed = [r for r in runs if r.get("status") == "completed" and r.get("conclusion") not in {"success", "neutral", "skipped"}]
    pending = [r for r in runs if r.get("status") != "completed"]

    if failed:
        names = ", ".join(str(r.get("workflowName") or r.get("name")) for r in failed)
        return RepoPulse(repo, "attention", f"failed: {names}", failed, pending)
    if pending:
        names = ", ".join(str(r.get("workflowName") or r.get("name")) for r in pending)
        return RepoPulse(repo, "pending", f"pending: {names}", failed, pending)
    return RepoPulse(repo, "healthy", "latest workflow runs healthy", failed, pending)


def update_streak(repo: str, pulse: RepoPulse) -> tuple[int, bool]:
    state = load_state()
    repo_state = state.setdefault("repos", {}).setdefault(repo, {})
    previous = repo_state.get("state")
    streak = int(repo_state.get("streak", 0))

    if pulse.state == "healthy":
        streak += 1
    elif pulse.state == "attention":
        streak = 0

    recovered = previous == "attention" and pulse.state == "healthy"
    repo_state.update({"state": pulse.state, "streak": streak, "updated_at": int(time.time())})
    save_state(state)
    return streak, recovered


def render(pulse: RepoPulse, streak: int, recovered: bool) -> None:
    if pulse.state == "healthy":
        marker = "✅ HEALTHY"
    elif pulse.state == "pending":
        marker = "⏳ PENDING"
    else:
        marker = "❌ ATTENTION"

    extras: list[str] = []
    if recovered:
        extras.append("🚀 RECOVERY")
    if streak >= STREAK_TARGET and pulse.state == "healthy":
        extras.append(f"🔥 STREAK x{streak}")

    suffix = f" | {' | '.join(extras)}" if extras else ""
    print(f"{marker} {pulse.repo}: {pulse.details}{suffix}")

    for run in pulse.failed_runs:
        print(f"   ↳ {run.get('workflowName') or run.get('name')}: {run.get('conclusion')} {run.get('url', '')}")


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid config JSON: {exc}") from exc


def bounded_repair(repo: str, pulse: RepoPulse, config_path: Path) -> bool:
    """Run an exact allow-listed local repair command. Never guesses or mutates remote settings."""
    if pulse.state != "attention":
        return False

    config = load_config(config_path)
    rules = config.get("repairs", [])
    for rule in rules:
        if not rule.get("enabled", False):
            continue
        workflow = str(rule.get("workflow", ""))
        command = rule.get("command")
        cwd_value = rule.get("cwd")
        if not workflow or not isinstance(command, list) or not command:
            continue
        if not all(isinstance(part, str) for part in command):
            continue

        matched = any((r.get("workflowName") or r.get("name")) == workflow for r in pulse.failed_runs)
        if not matched:
            continue

        cwd = Path(cwd_value).expanduser().resolve() if cwd_value else None
        if cwd is None or not (cwd / ".git").exists():
            print(f"🛑 Repair rule for {workflow} skipped: cwd must be an explicit local Git repository.")
            continue

        print(f"🔧 BOUNDED REPAIR {repo}: {workflow}")
        result = _run(command, cwd=cwd)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            print(f"❌ Repair command failed with exit {result.returncode}")
            return False
        print("🧪 Repair command completed; Cyber CPR will verify on the next pulse.")
        return True
    return False


def check_repos(repos: list[str], config: Path | None = None, repair: bool = False) -> int:
    overall = 0
    for repo in repos:
        try:
            pulse = pulse_repo(repo)
        except Exception as exc:  # noqa: BLE001
            print(f"❌ ATTENTION {repo}: {exc}")
            overall = 1
            continue
        streak, recovered = update_streak(repo, pulse)
        render(pulse, streak, recovered)
        if pulse.state == "attention":
            overall = 1
            if repair and config is not None:
                bounded_repair(repo, pulse, config)
    return overall


def main() -> int:
    parser = argparse.ArgumentParser(prog="cyber-cpr", description="Defensive repository health and recovery heartbeat")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run one heartbeat check")
    check.add_argument("repos", nargs="+")
    check.add_argument("--config", type=Path, default=Path("config.json"))
    check.add_argument("--repair", action="store_true", help="Run only explicitly enabled allow-listed local repair rules")

    watch = subparsers.add_parser("watch", help="Continuously check repositories")
    watch.add_argument("repos", nargs="+")
    watch.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    watch.add_argument("--config", type=Path, default=Path("config.json"))
    watch.add_argument("--repair", action="store_true")

    args = parser.parse_args()
    ensure_prerequisites()

    if args.command == "check":
        return check_repos(args.repos, args.config, args.repair)

    interval = max(60, int(args.interval))
    print(f"🚑 Cyber CPR watch active every {interval}s. Ctrl-C to stop.")
    try:
        while True:
            check_repos(args.repos, args.config, args.repair)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nCyber CPR stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
