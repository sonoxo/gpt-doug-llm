#!/usr/bin/env python3
"""Clone verified public GitHub targets into isolated, restorable cloud Git caches.

The default mode clones source code without running it, verifies every checked-out
Git blob exists offline, and drops the redundant checkout while retaining Git
objects. --verify-only restores the Git working tree with network lazy-fetching
disabled, verifies the pinned SHA, and compacts the checkout again.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

CATEGORIES = ("global", "ai", "pqc", "sonoxo")
EXPECTED_COUNTS = {"global": 20, "ai": 20, "pqc": 20, "sonoxo": 25}
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


def git(args: list[str], *, cwd: Path | None = None, timeout: int = 120,
        extra_env: dict[str, str] | None = None, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"})
    if extra_env:
        env.update(extra_env)
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args],
                          cwd=cwd, input=stdin, capture_output=True,
                          timeout=timeout, env=env, check=False)


def must(result: subprocess.CompletedProcess, label: str) -> bytes:
    if result.returncode:
        reason = result.stderr.decode("utf-8", "replace")[-900:]
        raise RuntimeError(f"{label}: {reason}")
    return result.stdout


def validate_name(name: str) -> None:
    if (not isinstance(name, str) or not REPO_RE.fullmatch(name)
            or any(part in (".", "..") for part in name.split("/"))):
        raise ValueError(f"Unsafe repository name: {name!r}")


def select_targets(target_file: Path, category: str, shard: int, shards: int) -> list[str]:
    data = json.loads(target_file.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported target schema")
    if category not in CATEGORIES or not 0 <= shard < shards or shards < 1:
        raise ValueError("Invalid category or shard arguments")
    groups = data.get("categories")
    if not isinstance(groups, dict):
        raise ValueError("Targets have no categories")
    for key, expected in EXPECTED_COUNTS.items():
        names = groups.get(key)
        if not isinstance(names, list) or len(names) != expected:
            raise ValueError(f"Expected exactly {expected} targets in {key}")
        for name in names:
            validate_name(name)
        if len({n.lower() for n in names}) != len(names):
            raise ValueError(f"Duplicate names within {key}")
    return groups[category][shard::shards]


def size_bytes(path: Path) -> int:
    result = subprocess.run(["du", "-sk", str(path)], capture_output=True, timeout=45, check=True)
    return int(result.stdout.split()[0]) * 1024


def tracked_blobs_present(repo: Path) -> int:
    """Check all tracked blobs without Git downloading missing promised objects."""
    entries = must(git(["ls-tree", "-rz", "HEAD"], cwd=repo), "git ls-tree")
    blobs = set()
    for entry in entries.split(b"\x00"):
        if not entry:
            continue
        metadata = entry.split(b"\t", 1)[0].split()
        if len(metadata) != 3:
            raise RuntimeError("Invalid git tree entry")
        if metadata[1] == b"blob":
            blobs.add(metadata[2])
    if blobs:
        check = must(git(["cat-file", "--batch-check=%(objectname) %(objecttype)"],
                         cwd=repo, timeout=240, extra_env={"GIT_NO_LAZY_FETCH": "1"},
                         stdin=b"\n".join(sorted(blobs)) + b"\n"),
                     "git cat-file")
        for line in check.splitlines():
            if not line.endswith(b" blob"):
                raise RuntimeError("Git tree has missing or non-blob objects: " + line.decode("ascii", "replace"))
        if len(check.splitlines()) != len(blobs):
            raise RuntimeError("Git blob validation count mismatch")
    return len(blobs)


def compact_checkout(repo: Path) -> None:
    if not (repo / ".git").is_dir():
        raise RuntimeError(f"Missing .git directory: {repo}")
    for child in repo.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def snapshot_head(repo: Path) -> str:
    sha = must(git(["rev-parse", "--verify", "HEAD"], cwd=repo), "git rev-parse").decode().strip()
    if not SHA_RE.fullmatch(sha):
        raise RuntimeError(f"Unexpected commit SHA: {sha}")
    return sha


def clone_one(name: str, root: Path) -> dict:
    result: dict = {"repo": name, "status": "failed"}
    try:
        validate_name(name)
        dest = root / "repos" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            raise RuntimeError("Destination already exists (refusing to overwrite)")
        cloned = git(["clone", "--depth=1", "--filter=blob:none", "--single-branch", "--no-tags",
                      "https://github.com/" + name + ".git", str(dest)], timeout=600)
        must(cloned, "git clone")
        result["sha"] = snapshot_head(dest)
        result["tracked_blobs"] = tracked_blobs_present(dest)
        result["checkout_bytes"] = size_bytes(dest)
        compact_checkout(dest)
        result["git_bytes"] = size_bytes(dest)
        result["status"] = "cloned"
    except Exception as exc:
        result["error"] = str(exc)[-900:]
    return result


def verify_one(name: str, sha: str, root: Path) -> dict:
    result: dict = {"repo": name, "status": "failed", "expected_sha": sha}
    try:
        validate_name(name)
        if not SHA_RE.fullmatch(sha):
            raise ValueError("Invalid expected SHA")
        repo = root / "repos" / name
        if not (repo / ".git").is_dir():
            raise RuntimeError("Git object archive absent")
        head = snapshot_head(repo)
        if head != sha:
            raise RuntimeError(f"Unexpected commit {head}")
        result["tracked_blobs"] = tracked_blobs_present(repo)
        result["recovered_bytes"] = 0
        try:
            must(git(["-c", "remote.origin.promisor=false", "reset", "--hard", "-q", "HEAD"],
                     cwd=repo, timeout=480, extra_env={"GIT_NO_LAZY_FETCH": "1"}), "offline git reset")
            result["recovered_bytes"] = size_bytes(repo)
            status = must(git(["status", "--porcelain", "--untracked-files=no"], cwd=repo), "git status")
            if status.strip():
                raise RuntimeError("Reconstructed checkout has tracked changes")
            result["status"] = "restored_offline"
        finally:
            compact_checkout(repo)
        result["sha"] = head
    except Exception as exc:
        result["error"] = str(exc)[-900:]
    return result


def run(args: argparse.Namespace) -> int:
    category = args.category
    shard = args.shard
    shards = args.shard_count
    root = args.destination / category / f"shard-{shard}"
    root.mkdir(parents=True, exist_ok=True)
    chosen = select_targets(args.targets, category, shard, shards)
    mode = "verify" if args.verify_only else "clone"
    report_path = root / ("verify-report.json" if args.verify_only else "clone-report.json")
    if args.verify_only:
        original_path = root / "clone-report.json"
        if not original_path.is_file():
            raise RuntimeError("Clone report not restored from cache")
        original = json.loads(original_path.read_text(encoding="utf-8"))
        entries = {r["repo"]: r for r in original.get("repositories", [])}
        if set(entries) != set(chosen) or any(entries[n]["status"] != "cloned" for n in chosen):
            raise RuntimeError("Cached clone report does not match pinned shard targets")
        futures_args = [(name, entries[name]["sha"], root) for name in chosen]
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            results = list(pool.map(lambda t: verify_one(*t), futures_args))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda name: clone_one(name, root), chosen))
    for item in results:
        print(f"{mode}: {item['status']} {item['repo']} {item.get('sha','')} {item.get('error','')}", flush=True)
    success = "restored_offline" if args.verify_only else "cloned"
    report = {"schema_version": 1,
              "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "category": category, "shard": shard, "shard_count": shards,
              "mode": mode, "selected": len(chosen),
              "success": sum(x["status"] == success for x in results),
              "total_git_bytes": sum(x.get("git_bytes", 0) for x in results),
              "repositories": results}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{mode}: {category} shard {shard} success {report['success']}/{len(chosen)}, bytes={report['total_git_bytes']}, report={report_path}", flush=True)
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### {mode} {category}/{shard}: {report['success']}/{len(chosen)}\n")
    return 0 if report["success"] == len(chosen) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", choices=CATEGORIES, required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=4)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--targets", type=Path, default=Path("data/github-cloud-library-targets.json"))
    parser.add_argument("--verify-only", action="store_true")
    opts = parser.parse_args()
    try:
        return run(opts)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
