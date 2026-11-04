#!/usr/bin/env bash
# Start an actual local GPT-DOUG Cinema Studio. No paid APIs or Python packages.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then PY="$(command -v python3)";
elif command -v python3.12 >/dev/null 2>&1; then PY="$(command -v python3.12)";
else echo "Free Python 3 is required. On Mac: brew install python@3.12" >&2; exit 2; fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1 && [[ "${CINEMA_AUTO_FFMPEG:-1}" == "1" ]]; then
    echo "Installing the FREE FFmpeg video editor with Homebrew. No video AI model is being downloaded."
    brew install ffmpeg
  else
    echo "FFmpeg is needed for real MP4 exports. Install free: brew install ffmpeg" >&2
  fi
fi
if command -v curl >/dev/null 2>&1 && curl --noproxy '*' -fsS --max-time 2 http://127.0.0.1:8793/api/health | grep -q '"ok":true'; then
  echo 'Cinema Studio already running: http://127.0.0.1:8793/'
  if command -v open >/dev/null 2>&1; then open 'http://127.0.0.1:8793/'; fi
  exit 0
fi
echo 'GPT-DOUG CINEMA // FREE LOCAL STUDIO / http://127.0.0.1:8793/'
echo 'Keep this Terminal open. Ctrl-C stops the local app and queued jobs.'
exec "$PY" -m cinema_studio.server
