#!/usr/bin/env bash
# Start the exact seven-problem research suite from any working directory.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'GPT-DOUG MILLENNIUM FORGE: Python 3.9+ required' >&2
  exit 127
fi
cd "$ROOT"
if [[ $# -eq 0 ]]; then set -- demo; fi
exec python3 -m research_lab.millennium_forge "$@"
