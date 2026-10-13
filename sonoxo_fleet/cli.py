"""CLI for the read-only Sonoxo public GitHub portfolio auditor."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .core import (
    AuditError, OWNER, SCHEMA, plan_upgrade, public_repo_inventory,
    snapshot_from_repos, validate_snapshot, write_reports,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO_ROOT / "data" / "sonoxo_fleet" / "observed_public_repositories.json"
PRS = REPO_ROOT / "data" / "sonoxo_fleet" / "observed_open_prs.json"
DEFAULT_OUTPUT = Path("build/sonoxo-fleet")


def load_snapshot(path: Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(doc, dict) and doc.get("schema") == SCHEMA:
        return validate_snapshot(doc)
    if isinstance(doc, dict) and doc.get("schema") == "sonoxo.portfolio.observation.v1":
        return snapshot_from_repos(
            doc["repositories"], observed_at=doc["observed_at"], source=doc["source"],
        )
    raise AuditError("snapshot must be an official observation or a verified signed snapshot")


def load_prs(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != "sonoxo.portfolio.pr-observation.v1":
        raise AuditError("invalid PR snapshot schema")
    return doc["pull_requests"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="gpt-doug-fleet", description="Read-only 209+ repository Sonoxo portfolio auditor"
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="print read-only permissions and scope")
    audit = sub.add_parser("audit", help="build offline repository dashboard and change review plan")
    audit.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    audit.add_argument("--prs", type=Path, default=PRS)
    audit.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    audit.add_argument("--force", action="store_true")
    live = sub.add_parser("sync-public", help="explicit opt-in: read public GitHub repo inventory")
    live.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    live.add_argument("--force", action="store_true")
    args = p.parse_args(argv)

    if args.command == "status":
        print(json.dumps({
            "system": "GPT-DOUG SONOXO FLEET",
            "scope": "SONOXO_PUBLIC_REPOSITORIES_ONLY",
            "inventory_file": str(SNAPSHOT),
            "default_network_actions": 0,
            "remote_repo_writes": False,
            "automatic_merges": False,
            "force_push": False,
            "private_repositories_discovered": False,
            "cross_repository_credentials_required": False,
            "manual_human_review_required": True,
        }, indent=2))
        return 0
    try:
        if args.command == "audit":
            snapshot = load_snapshot(args.snapshot)
            prs = load_prs(args.prs)
        else:
            snapshot = public_repo_inventory(token=os.environ.get("GITHUB_TOKEN"))
            # Open PRs are not queried during an opt-in inventory refresh:
            # the observed PR list remains explicit / versioned, not guessed.
            prs = load_prs(PRS)
        summary = write_reports(snapshot, args.output, prs=prs, force=args.force)
        # Store a normalized, integrity-hashed snapshot only in the build folder,
        # not in source directories or another GitHub repository.
        (args.output / "snapshot.json").write_text(
            json.dumps(snapshot, indent=2) + "\n", encoding="utf-8",
        )
        print(json.dumps({
            "ok": True, "scope": summary["scope"],
            "repositories": summary["repositories_indexed"],
            "core_repositories": summary["core_repositories"],
            "observed_open_prs": summary["observed_open_prs"],
            "snapshot_digest": summary["source_sha256"],
            "dashboard": str(args.output / "portfolio.html"),
            "policy": "REVIEW_ONLY_NO_REPO_WRITES",
        }, indent=2))
        return 0
    except (AuditError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "remote_repo_writes": 0}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
