#!/usr/bin/env python3
"""XZSWEEP: repository freshness maintenance without meaningless source churn.

A file becomes due when neither its last content-changing Git commit nor its last
XZSWEEP review (for the same content hash) occurred within the configured window.
Due files are reviewed, safe deterministic repairs are applied where possible,
and the review is recorded in .xzsweep/freshness.json.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / ".xzsweep" / "freshness.json"
SELF_EXCLUDES = {".xzsweep/freshness.json"}
SAFE_EOF_EXTENSIONS = {
    ".bash", ".cfg", ".conf", ".css", ".csv", ".env", ".example", ".gql",
    ".graphql", ".html", ".ini", ".js", ".json", ".jsonl", ".jsx", ".md",
    ".mjs", ".cjs", ".py", ".scss", ".sh", ".sql", ".toml", ".ts", ".tsx",
    ".tsv", ".txt", ".xml", ".yaml", ".yml", ".zsh",
}
SAFE_EOF_NAMES = {
    ".dockerignore", ".editorconfig", ".env.example", ".gitattributes", ".gitignore",
    "Dockerfile", "LICENSE", "Makefile", "Modelfile", "Procfile",
}


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def tracked_files() -> list[str]:
    raw = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return sorted(
        path for path in raw.decode("utf-8").split("\0")
        if path and path not in SELF_EXCLUDES
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def last_git_touch(path: str) -> datetime | None:
    stamp = git("log", "-1", "--format=%cI", "--", path)
    return parse_iso(stamp)


def load_previous(report: Path) -> dict[str, Any]:
    if not report.exists():
        return {}
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
        files = payload.get("files", {})
        return files if isinstance(files, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def is_probably_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    try:
        data.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def safe_for_eof_repair(path: Path) -> bool:
    return path.name in SAFE_EOF_NAMES or path.suffix.lower() in SAFE_EOF_EXTENSIONS


def validate(path: str, data: bytes) -> list[str]:
    issues: list[str] = []
    if is_probably_binary(data):
        return issues
    text = data.decode("utf-8")
    suffix = Path(path).suffix.lower()
    try:
        if suffix == ".json":
            json.loads(text)
        elif suffix == ".jsonl":
            for line_no, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as exc:
                        issues.append(f"jsonl line {line_no}: {exc.msg}")
        elif suffix == ".py":
            ast.parse(text, filename=path)
    except (json.JSONDecodeError, SyntaxError) as exc:
        issues.append(str(exc))
    return issues


def effective_touch(
    git_touch: datetime | None,
    previous: dict[str, Any],
    current_hash: str,
) -> tuple[datetime | None, str]:
    review_touch = None
    if previous.get("sha256") == current_hash:
        review_touch = parse_iso(previous.get("reviewed_at"))
    candidates = [(git_touch, "git"), (review_touch, "xzsweep")]
    candidates = [(dt, source) for dt, source in candidates if dt is not None]
    return max(candidates, default=(None, "unknown"), key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc))


def run(hours: float, apply: bool, report: Path) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    previous = load_previous(report)
    records: dict[str, Any] = {}
    stale_paths: list[str] = []
    repaired_paths: list[str] = []
    validation_issues: dict[str, list[str]] = {}

    for rel in tracked_files():
        path = ROOT / rel
        if not path.is_file():
            continue
        data = path.read_bytes()
        before_hash = sha256(data)
        git_touch = last_git_touch(rel)
        prior = previous.get(rel, {}) if isinstance(previous.get(rel), dict) else {}
        effective, source = effective_touch(git_touch, prior, before_hash)
        due = effective is None or effective < cutoff
        binary = is_probably_binary(data)
        actions: list[str] = []

        if due:
            stale_paths.append(rel)
            if apply and not binary and data and not data.endswith(b"\n") and safe_for_eof_repair(path):
                path.write_bytes(data + b"\n")
                data += b"\n"
                actions.append("append_eof_newline")
                repaired_paths.append(rel)

        issues = validate(rel, data) if due else []
        if issues:
            validation_issues[rel] = issues

        current_hash = sha256(data)
        reviewed_at = iso_utc(now) if due else prior.get("reviewed_at") if prior.get("sha256") == current_hash else None
        records[rel] = {
            "sha256": current_hash,
            "size": len(data),
            "binary": binary,
            "git_touched_at": iso_utc(git_touch) if git_touch else None,
            "reviewed_at": reviewed_at,
            "was_due": due,
            "freshness_source_before_review": source,
            "actions": actions,
            "validation_issues": issues,
        }

    payload = {
        "schema": "xzsweep.freshness.v1",
        "generated_at": iso_utc(now),
        "cutoff_at": iso_utc(cutoff),
        "freshness_window_hours": hours,
        "mode": "apply" if apply else "check",
        "tracked_files_reviewed": len(records),
        "due_files_reviewed": len(stale_paths),
        "content_repairs": len(repaired_paths),
        "validation_issue_files": len(validation_issues),
        "due_paths": stale_paths,
        "repaired_paths": repaired_paths,
        "validation_issues": validation_issues,
        "files": records,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "tracked": len(records),
        "due_reviewed": len(stale_paths),
        "content_repairs": len(repaired_paths),
        "validation_issue_files": len(validation_issues),
        "report": str(report.relative_to(ROOT)),
    }
    print("XZSWEEP " + json.dumps(summary, sort_keys=True))
    if validation_issues:
        print("XZSWEEP validation findings were recorded in the report.", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Review repository paths older than a freshness window.")
    parser.add_argument("--hours", type=float, default=24.0, help="Freshness window in hours (default: 24).")
    parser.add_argument("--apply", action="store_true", help="Apply safe deterministic repairs while reviewing due paths.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Output freshness ledger path.")
    args = parser.parse_args()
    report = args.report if args.report.is_absolute() else ROOT / args.report
    return run(args.hours, args.apply, report)


if __name__ == "__main__":
    raise SystemExit(main())
