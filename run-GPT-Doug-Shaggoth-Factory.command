#!/usr/bin/env bash
# GPT-Doug-Shaggoth one-command local autonomous drafting factory.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'SHAGGOTH FACTORY: Python 3.9+ is required' >&2
  exit 127
fi
cd "$ROOT"
exec python3 "$ROOT/gpt_zyra_shaggoth/factory.py" --demo-policy serve --demo "$@"
