#!/usr/bin/env bash
set -euo pipefail

# Resolve the host repository from THIS script, never from the caller's current
# working directory. This makes the launcher safe to run from xunidirect or any
# other repo/directory.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
APP="$ROOT/the-green-house/apps/worldmonitor"
PROFILE="$ROOT/the-green-house/config/worldmonitor-free-profile.json"
OVERLAY="$ROOT/the-green-house/branding/green-house-overlay.js"
HOST="${GREEN_HOUSE_HOST:-127.0.0.1}"

# If the caller did not request a specific port, select the first free local
# port in a small predictable range so an existing dev server cannot block boot.
if [ -z "${DEV_PORT:-}" ]; then
  DEV_PORT="$(python3 - <<'PY'
import socket
for port in range(3000, 3021):
    with socket.socket() as s:
        try:
            s.bind(('127.0.0.1', port))
        except OSError:
            continue
        print(port)
        raise SystemExit(0)
raise SystemExit('No free Green House port found in 3000-3020')
PY
)"
fi
URL="http://${HOST}:${DEV_PORT}"

printf '\n🌿 THE GREEN HOUSE — WorldMonitor\n'
printf '   repo: %s\n' "$ROOT"
printf '   mode: zero-cost-first / public-data-first\n'
printf '   profile: %s\n' "$PROFILE"
printf '   url: %s\n\n' "$URL"

if [ ! -d "$ROOT/.git" ]; then
  printf '❌ Green House host repository is missing at: %s\n' "$ROOT" >&2
  exit 2
fi

# Ensure the complete pinned upstream source exists locally.
git -C "$ROOT" submodule sync --recursive
git -C "$ROOT" submodule update --init --recursive the-green-house/apps/worldmonitor

if [ ! -f "$APP/package.json" ]; then
  printf '❌ WorldMonitor source did not initialize at: %s\n' "$APP" >&2
  exit 3
fi

cd "$APP"

export DEV_PORT
export VITE_VARIANT="${VITE_VARIANT:-full}"
export VITE_MAP_INTERACTION_MODE="${VITE_MAP_INTERACTION_MODE:-3d}"

# Keep a user-supplied WorldMonitor key if one already exists. The baseline
# Green House surface does not require it, but explicitly supplied credentials
# should not be discarded.
if [ -n "${WORLDMONITOR_API_KEY:-${WM_API_KEY:-}}" ]; then
  printf '🔑 Optional WorldMonitor API credential detected; preserving it.\n'
else
  printf '🆓 No WorldMonitor API key required for baseline launch.\n'
fi

# Apply an idempotent runtime-only Green House visual identity while preserving
# the upstream WorldMonitor source, license, and attribution inside the submodule.
mkdir -p public
cp "$OVERLAY" public/green-house-overlay.js
python3 - <<'PY'
from pathlib import Path

path = Path('index.html')
text = path.read_text(encoding='utf-8')
tag = '    <script type="module" src="/green-house-overlay.js"></script>'
if tag not in text:
    text = text.replace('</head>', f'{tag}\n  </head>', 1)
    path.write_text(text, encoding='utf-8')
PY

if [ ! -d node_modules ]; then
  printf '📦 Installing WorldMonitor dependencies...\n'
  npm install
fi

printf '\n🌎 Starting The Green House intelligence surface...\n'
printf '   upstream source: koala73/worldmonitor (AGPL-3.0-only)\n'
printf '   Green House branding overlay: active\n'
printf '   browser target: %s\n\n' "$URL"

# Run Vite in the background so we can health-check it and open the browser.
npm run dev -- --host "$HOST" --port "$DEV_PORT" --strictPort &
SERVER_PID=$!

cleanup() {
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

READY=0
for ((i=0; i<120; i++)); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    printf '\n❌ WorldMonitor dev server exited before becoming ready.\n' >&2
    wait "$SERVER_PID"
    exit $?
  fi
  if curl -fsS --max-time 2 "$URL" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  printf '\n❌ Timed out waiting for %s\n' "$URL" >&2
  exit 4
fi

printf '\n✅ THE GREEN HOUSE ONLINE: %s\n' "$URL"

# Open the dashboard automatically on desktop systems.
case "$(uname -s)" in
  Darwin)
    open "$URL" >/dev/null 2>&1 || true
    ;;
  Linux)
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$URL" >/dev/null 2>&1 || true
    fi
    ;;
esac

printf '🟢 Browser launch requested. Keep this terminal open while Green House runs.\n'

wait "$SERVER_PID"
