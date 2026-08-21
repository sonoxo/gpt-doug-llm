#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BASE_MODEL="${XUNIA_BASE_MODEL:-qwen2.5-coder:7b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "XUNIA ERROR // Ollama is not installed or is not on PATH." >&2
  exit 1
fi

python3 xunia_godis.py install --base-model "$BASE_MODEL"
python3 xunia_godis.py doctor

echo
echo "Ready: ollama run gpt-xunia-godis"
