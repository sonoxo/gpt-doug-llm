#!/usr/bin/env bash
# GPT-DOUG Motion-1: Mac launcher — opens the local server before optional training.
# Free dependencies only. Keeps the browser service attached to this Terminal.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3.12 >/dev/null 2>&1 && ! command -v python3.11 >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Installing free Python 3.12 with Homebrew (separate from Python 3.15)"
    brew install python@3.12
  else
    echo "Python 3.11 or 3.12 is required. Install free Python first." >&2
    exit 2
  fi
fi

PYTHON="$ROOT/open_video_model/.venv/bin/python"
if [[ ! -x "$PYTHON" ]] || ! "$PYTHON" -c 'import torch, PIL' >/dev/null 2>&1; then
  bash "$ROOT/open_video_model/setup_mac.sh"
fi

# Start local studio immediately. Run a bounded training job in the SAME
# Terminal session, supervised by the launcher and stopped when it exits.
CHECKPOINT="$HOME/.local/share/gpt-doug/motion-1/motion1.pt"
LOG_DIR="$HOME/.local/share/gpt-doug/motion-1"
TRAIN_PID=""
cleanup() {
  if [[ -n "$TRAIN_PID" ]]; then
    kill "$TRAIN_PID" >/dev/null 2>&1 || true
    wait "$TRAIN_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ ! -f "$CHECKPOINT" ]]; then
  STEPS="${MOTION_TRAIN_STEPS:-500}"
  if [[ ! "$STEPS" =~ ^[0-9]+$ ]] || (( STEPS < 1 || STEPS > 100000 )); then
    echo "MOTION_TRAIN_STEPS must be a whole number 1 through 100000." >&2
    exit 2
  fi
  if [[ "${MOTION_AUTOTRAIN:-1}" != "0" ]]; then
    mkdir -p "$LOG_DIR"
    echo "Starting local Motion-1 starter training (${STEPS} steps)."
    echo "Training log: $LOG_DIR/training.log"
    echo "The studio will open before training finishes; its AI button unlocks once a checkpoint exists."
    "$PYTHON" -m open_video_model train --steps "$STEPS" > "$LOG_DIR/training.log" 2>&1 &
    TRAIN_PID=$!
  else
    echo "Starter training disabled. To enable AI generation, run:"
    echo "  $PYTHON -m open_video_model train --steps 500"
  fi
fi

echo "Launching free local studio at http://127.0.0.1:8792/"
echo "Keep this Terminal window open. Press Ctrl-C to shut down."
"$PYTHON" -m open_video_model studio
