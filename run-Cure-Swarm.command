#!/usr/bin/env bash
# Open an offline, interactive Cure Swarm terminal without extra packages.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'BIO-GPT: Python 3.9+ is required' >&2
  exit 127
fi
cd "$ROOT"
if [[ $# -eq 0 ]]; then
  exec python3 -m research_lab.cure_swarm_terminal
fi
if [[ "$1" == "--once" ]]; then
  shift
  exec python3 -m research_lab.cure_swarm_terminal --once "$@"
fi
exec python3 -m research_lab.cure_swarm "$@"
