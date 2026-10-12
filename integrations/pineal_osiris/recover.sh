#!/bin/sh
# Recovery specifically for OSIRIS npm ENOSPC, including a fresh bootstrap.
# Requires: Python 3.10+, Git, curl, npm. Does not delete user documents.
set -eu
SOURCE='https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/feature/pineal-osiris-local-clone/integrations/pineal_osiris'
WORKTREE=${OSIRIS_WORKTREE:-"$HOME/.local/share/gpt-doug/osiris-ui"}
BOOTSTRAP="$HOME/Downloads/gpt-doug-osiris-bootstrap.sh"
MIN_MB=${OSIRIS_MIN_FREE_MB:-4096}
if [ "${1:-}" = '--check' ]; then
  echo "OSIRIS checkout to repair: $WORKTREE"
  echo "Will remove only this checkout's node_modules after verifying its official Git origin."
  echo "Will clear npm's shared *download cache* (not other projects' installed packages)."
  echo "Will require $MIN_MB MiB free disk before retrying npm install."
  python3 - "$WORKTREE" <<'PY'
import pathlib, shutil, sys
p = pathlib.Path(sys.argv[1]).expanduser()
while not p.exists():
    if p == p.parent:
        break
    p = p.parent
if p.exists():
    print("Disk free: %s MiB" % (shutil.disk_usage(p).free // 1048576))
PY
  exit 0
fi
if [ "${1:-}" != '' ]; then echo 'Usage: sh recover.sh [--check]' >&2; exit 2; fi
for cmd in git python3 npm curl; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing dependency: $cmd" >&2; exit 2; }
done
python3 - "$WORKTREE" <<'PY'
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

target = Path(sys.argv[1]).expanduser().absolute()
if target.is_symlink() or not (target / ".git").is_dir():
    raise SystemExit("Refusing repair: expected real OSIRIS Git checkout not found.")
origin = subprocess.check_output(["git", "-C", str(target), "remote", "get-url", "origin"], text=True).strip()
if origin != "https://github.com/simplifaisoul/osiris.git":
    raise SystemExit("Refusing repair: unexpected Git repository origin.")
root = subprocess.check_output(["git", "-C", str(target), "rev-parse", "--show-toplevel"], text=True).strip()
if Path(root).resolve() != target.resolve():
    raise SystemExit("Refusing repair: checkout root mismatch.")
if not (target / "package-lock.json").is_file() or not (target / "LICENSE").is_file():
    raise SystemExit("Refusing repair: expected upstream source files missing.")
try:
    with urlopen("http://127.0.0.1:3000/api/health", timeout=1.5) as response:
        health = json.load(response)
        if health.get("platform") == "OSIRIS" and health.get("status") == "serving":
            raise SystemExit("OSIRIS is already running. Stop it before repairing.")
except (URLError, HTTPError, TimeoutError, OSError, ValueError):
    pass
modules = target / "node_modules"
if modules.is_symlink() or (modules.exists() and not modules.is_dir()):
    raise SystemExit("Refusing repair: node_modules is not a regular directory.")
before = shutil.disk_usage(target).free // (1024 * 1024)
if modules.is_dir():
    print("Removing only incomplete OSIRIS node_modules ...", flush=True)
    shutil.rmtree(modules)
after = shutil.disk_usage(target).free // (1024 * 1024)
print(f"OSIRIS dependency cleanup: {before} -> {after} MiB free", flush=True)
PY
echo 'Cleaning regenerable shared npm download cache (does not remove other projects installations)...'
npm cache clean --force
python3 - "$WORKTREE" "$MIN_MB" <<'PY'
from pathlib import Path
import shutil
import sys
try:
    needed = int(sys.argv[2])
except ValueError:
    raise SystemExit("OSIRIS_MIN_FREE_MB must be numeric")
if not 512 <= needed <= 50000:
    raise SystemExit("OSIRIS_MIN_FREE_MB must be 512..50000")
available = shutil.disk_usage(Path(sys.argv[1]).expanduser()).free // (1024 * 1024)
print(f"Free space after repair: {available} MiB (recommended {needed} MiB)")
if available < needed:
    raise SystemExit("OSIRIS remains low on free disk. Free more macOS storage or use OSIRIS_WORKTREE on a volume with >= 4 GiB available before retrying.")
PY
mkdir -p "$HOME/Downloads"
curl -fsSLo "$BOOTSTRAP" "$SOURCE/bootstrap.sh"
echo 'Disk preflight passed. Resuming verified feature-branch bootstrap...'
exec sh "$BOOTSTRAP"
