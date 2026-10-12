#!/usr/bin/env python3
"""Conservative disk-space diagnostics and explicit OSIRIS-only repair.

No global filesystem cleanup is performed. Reclaiming npm's shared cache
requires an explicit --npm-cache flag and is never done during startup.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

OFFICIAL_ORIGIN = "https://github.com/simplifaisoul/osiris.git"
DEFAULT_WORKTREE = Path.home() / ".local/share/gpt-doug/osiris-ui"
MIB = 1024 * 1024
DEFAULT_MIN_FREE_MB = 4096


def closest_existing(path: Path) -> Path:
    current = path.expanduser().absolute()
    while not current.exists():
        parent = current.parent
        if parent == current:
            raise ValueError("no existing parent for disk usage check")
        current = parent
    return current


def free_mb(path: Path) -> int:
    return shutil.disk_usage(closest_existing(path)).free // MIB


def preflight(path: Path, minimum_mb: int = DEFAULT_MIN_FREE_MB) -> dict:
    if not 512 <= minimum_mb <= 50000:
        raise ValueError("minimum free-space threshold must be 512..50000 MiB")
    available = free_mb(path)
    result = {
        "available_mib": available,
        "recommended_mib": minimum_mb,
        "enough_free_space": available >= minimum_mb,
    }
    if result["enough_free_space"]:
        print(f"OSIRIS disk preflight OK: {available} MiB available, "
              f"{minimum_mb} MiB recommended.")
    else:
        print(f"OSIRIS install stopped BEFORE npm ci: only {available} MiB free; "
              f"{minimum_mb} MiB recommended.", file=sys.stderr)
        print("Recover only the incomplete OSIRIS installation and optionally "
              "the regenerable npm cache, then retry:", file=sys.stderr)
        print("  sh integrations/pineal_osiris/run.sh repair", file=sys.stderr)
        print("  sh integrations/pineal_osiris/run.sh repair-cache", file=sys.stderr)
        print("  df -h \"$HOME\"", file=sys.stderr)
        print("No files were removed by preflight.", file=sys.stderr)
    return result


def validate_checkout(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError("refusing symlinked OSIRIS worktree")
    path = path.expanduser().absolute()
    if not (path / ".git").is_dir() or (path / ".git").is_symlink():
        raise ValueError("refusing cleanup: OSIRIS Git checkout not found")
    remote = subprocess.run(
        ["git", "-C", str(path), "remote", "get-url", "origin"],
        text=True, capture_output=True, timeout=15, check=True,
    ).stdout.strip()
    if remote != OFFICIAL_ORIGIN:
        raise ValueError("refusing cleanup: unexpected Git remote")
    root = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        text=True, capture_output=True, timeout=15, check=True,
    ).stdout.strip()
    if Path(root).resolve() != path.resolve():
        raise ValueError("refusing cleanup: worktree is not repository root")
    if not (path / "package-lock.json").is_file() or not (path / "LICENSE").is_file():
        raise ValueError("refusing cleanup: expected OSIRIS source files absent")
    return path


def repair(path: Path, *, clear_npm_cache: bool = False, port: int = 3000) -> dict:
    path = validate_checkout(path)
    modules = path / "node_modules"
    if modules.is_symlink():
        raise ValueError("refusing to remove symlinked node_modules")
    if modules.exists() and not modules.is_dir():
        raise ValueError("refusing unexpected node_modules entry")
    # Avoid dismantling a server that is currently rendering or serving data.
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as response:
            if response.status == 200:
                payload = json.loads(response.read(8192))
                if payload.get("platform") == "OSIRIS" and payload.get("status") == "serving":
                    raise ValueError(f"OSIRIS is running on port {port}; stop it before repair")
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        pass
    before = free_mb(path)
    deleted = False
    if modules.is_dir():
        shutil.rmtree(modules)
        deleted = True
    if clear_npm_cache:
        # Explicit operator action; cache is shared across projects but is
        # regenerable. This NEVER removes other projects' installed packages.
        subprocess.run(["npm", "cache", "clean", "--force"], check=True, timeout=180)
    after = free_mb(path)
    print(f"OSIRIS-only repair: node_modules removed={deleted}; "
          f"free disk {before} -> {after} MiB.")
    if clear_npm_cache:
        print("Shared regenerable npm download cache cleared on explicit request.")
    else:
        print("Shared npm cache not touched. 'repair-cache' can reclaim more space.")
    return {"before_mib": before, "after_mib": after,
            "node_modules_removed": deleted, "npm_cache_cleared": clear_npm_cache}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="OSIRIS bounded disk diagnostics")
    p.add_argument("action", choices=("status", "preflight", "repair", "repair-cache"))
    p.add_argument("--worktree", type=Path, default=DEFAULT_WORKTREE)
    p.add_argument("--minimum-mb", type=int, default=DEFAULT_MIN_FREE_MB)
    p.add_argument("--port", type=int, default=3000)
    args = p.parse_args(argv)
    try:
        if args.action == "status":
            print(f"OSIRIS disk free: {free_mb(args.worktree)} MiB; "
                  f"recommended before npm install: {args.minimum_mb} MiB.")
            return 0
        if args.action == "preflight":
            return 0 if preflight(args.worktree, args.minimum_mb)["enough_free_space"] else 2
        repair(args.worktree, clear_npm_cache=args.action == "repair-cache", port=args.port)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"OSIRIS disk tool stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
