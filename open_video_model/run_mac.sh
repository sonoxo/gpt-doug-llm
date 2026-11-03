#!/usr/bin/env bash
# Free one-command GPT-DOUG Motion-1 Mac launcher.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if ! command -v python3.12 >/dev/null 2>&1 && ! command -v python3.11 >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing free Python 3.12 with Homebrew (isolated from Python 3.15)"
    brew install python@3.12
  else
    echo "Install free Python 3.12 from python.org or Homebrew before running." >&2
    exit 2
  fi
fi
if [[ ! -x "$ROOT/open_video_model/.venv/bin/python" ]]; then
  bash "$ROOT/open_video_model/setup_mac.sh"
fi
PYTHON="$ROOT/open_video_model/.venv/bin/python"
CHECKPOINT="$HOME/.local/share/gpt-doug/motion-1/motion1.pt"
if [[ ! -f "$CHECKPOINT" ]]; then
  STEPS="${MOTION_TRAIN_STEPS:-500}"
  if [[ ! "$STEPS" =~ ^[0-9]+$ ]] || (( STEPS < 1 || STEPS > 100000 )); then
    echo "MOTION_TRAIN_STEPS must be 1 to 100000" >&2
    exit 2
  fi
  echo "No trained Motion-1 weights yet. Training original starter model locally."
  "$PYTHON" -m open_video_model train --steps "$STEPS"
fi
"$PYTHON" -m open_video_model studio
