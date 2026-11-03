#!/usr/bin/env bash
# GPT-DOUG Motion-1 free Apple Silicon bootstrap; no Gatekeeper bypass.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON="$(command -v python3.12)"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="$(command -v python3.11)"
else
  echo "Python 3.11/3.12 required for tested setup. Free install: brew install python@3.12" >&2
  exit 2
fi
"$PYTHON" -m venv "$ROOT/open_video_model/.venv"
"$ROOT/open_video_model/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/open_video_model/.venv/bin/python" -m pip install -r "$ROOT/open_video_model/requirements.txt"
"$ROOT/open_video_model/.venv/bin/python" -m open_video_model doctor
echo "Local setup complete. No paid APIs."
echo "Train: open_video_model/.venv/bin/python -m open_video_model train --steps 500"
echo "Generate: open_video_model/.venv/bin/python -m open_video_model generate --prompt 'red circle moving right' --out ~/Movies/gpt-doug-motion.gif"
