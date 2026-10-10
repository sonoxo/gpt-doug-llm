#!/usr/bin/env bash
# Offline first. Use 'online --query ...' only for an explicit public API read.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'BIO-GPT: Python 3.9+ is required' >&2
  exit 127
fi
cd "$ROOT"
if [[ $# -eq 0 ]]; then set -- demo; fi
exec python3 -m research_lab.cure_swarm "$@"
