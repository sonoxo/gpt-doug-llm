#!/usr/bin/env bash
# GPT-DOUG Motion-1 // local-first launcher. Never requires a paid service.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG_DIR="$HOME/.local/share/gpt-doug/motion-1"
CHECKPOINT="$LOG_DIR/motion1.pt"
STATUS_FILE="$LOG_DIR/setup-status"
TRAIN_PID=""

if command -v python3.12 >/dev/null 2>&1; then
  SYSTEM_PY="$(command -v python3.12)"
elif command -v python3.11 >/dev/null 2>&1; then
  SYSTEM_PY="$(command -v python3.11)"
elif command -v brew >/dev/null 2>&1; then
  echo "Installing free Python 3.12 (avoids the Python 3.15 dependency mismatch)."
  brew install python@3.12
  SYSTEM_PY="$(command -v python3.12)"
else
  echo "Python 3.11 or 3.12 not installed. Free install: brew install python@3.12" >&2
  exit 2
fi

PY="$ROOT/open_video_model/.venv/bin/python"
mkdir -p "$LOG_DIR"
if [[ ! -x "$PY" ]]; then
  echo "Creating isolated local Motion-1 environment…"
  "$SYSTEM_PY" -m venv "$ROOT/open_video_model/.venv"
fi

# Preserve a previous working studio; never start a second listener on its port.
if command -v curl >/dev/null 2>&1 && curl --noproxy "*" -fsS --max-time 2 http://127.0.0.1:8792/api/health | grep -q '"ok":true'; then
  echo "Motion-1 Studio is already running: http://127.0.0.1:8792/"
  if command -v open >/dev/null 2>&1; then open "http://127.0.0.1:8792/"; fi
  exit 0
fi

STEPS="${MOTION_TRAIN_STEPS:-500}"
if [[ ! "$STEPS" =~ ^[0-9]+$ ]] || (( STEPS < 1 || STEPS > 100000 )); then
  echo "MOTION_TRAIN_STEPS must be a whole number 1–100000." >&2
  exit 2
fi

cleanup() {
  if [[ -n "$TRAIN_PID" ]]; then
    if command -v pkill >/dev/null 2>&1; then pkill -TERM -P "$TRAIN_PID" >/dev/null 2>&1 || true; fi
    kill "$TRAIN_PID" >/dev/null 2>&1 || true
    wait "$TRAIN_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ -f "$CHECKPOINT" ]]; then
  printf 'ready\n' > "$STATUS_FILE"
elif [[ "${MOTION_AUTOTRAIN:-1}" == "0" ]]; then
  printf 'not-started\n' > "$STATUS_FILE"
else
  # Installation and starter training are supervised under this Terminal.
  # The Python HTTP server starts immediately with stdlib; torch is imported only on inference.
  (
    set -e
    if ! "$PY" -c 'import torch, PIL' >/dev/null 2>&1; then
      printf 'installing\n' > "$STATUS_FILE"
      if ! bash open_video_model/setup_mac.sh > "$LOG_DIR/install.log" 2>&1; then
        printf 'failed\n' > "$STATUS_FILE"
        echo "Free dependency setup failed. Read $LOG_DIR/install.log" >&2
        exit 2
      fi
    fi
    if [[ ! -f "$CHECKPOINT" ]]; then
      printf 'training\n' > "$STATUS_FILE"
      if ! "$PY" -m open_video_model train --steps "$STEPS" > "$LOG_DIR/training.log" 2>&1; then
        printf 'failed\n' > "$STATUS_FILE"
        echo "Starter training failed. Read $LOG_DIR/training.log" >&2
        exit 2
      fi
    fi
    printf 'ready\n' > "$STATUS_FILE"
  ) &
  TRAIN_PID=$!
  echo "Free model setup / training launched. Status appears in the browser."
  echo "Install log: $LOG_DIR/install.log"
  echo "Training log: $LOG_DIR/training.log"
fi

echo "GPT-DOUG MOTION-1 // STUDIO LIVE AT http://127.0.0.1:8792/"
echo "Leave Terminal open. Ctrl-C stops the studio and supervised job."
"$PY" -m open_video_model studio
