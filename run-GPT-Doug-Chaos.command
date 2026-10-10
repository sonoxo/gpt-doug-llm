#!/usr/bin/env bash
# Opens the real local-only GPT-Doug-Chaos dashboard in the default browser.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'GPT-DOUG-CHAOS ERROR: Python 3.9+ is required.' >&2
  exit 127
fi
cd "$ROOT"
exec python3 "$ROOT/gpt_chaos/live_cube.py" serve "$@"
