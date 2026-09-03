#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "❌ Missing .venv. Run: bash install_free.sh"
  exit 1
fi
exec .venv/bin/python app.py
