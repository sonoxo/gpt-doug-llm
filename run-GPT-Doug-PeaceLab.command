#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ $# -eq 0 ]]; then set -- demo; fi
exec python3 -m peace_impact.cli "$@"
