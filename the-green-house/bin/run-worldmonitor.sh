#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
APP="$ROOT/the-green-house/apps/worldmonitor"
PROFILE="$ROOT/the-green-house/config/worldmonitor-free-profile.json"

printf '\n🌿 THE GREEN HOUSE — WorldMonitor\n'
printf '   mode: zero-cost-first / public-data-first\n'
printf '   profile: %s\n\n' "$PROFILE"

git -C "$ROOT" submodule update --init --recursive the-green-house/apps/worldmonitor

cd "$APP"

export DEV_PORT="${DEV_PORT:-3000}"
export VITE_VARIANT="${VITE_VARIANT:-full}"
export VITE_MAP_INTERACTION_MODE="${VITE_MAP_INTERACTION_MODE:-3d}"

# Green House baseline intentionally does not require the hosted WorldMonitor API.
unset WORLDMONITOR_API_KEY || true
unset WM_API_KEY || true

if [ ! -d node_modules ]; then
  npm install
fi

printf '🌎 Launching The Green House intelligence surface on port %s\n' "$DEV_PORT"
printf '   upstream source: koala73/worldmonitor (AGPL-3.0-only)\n\n'

exec npm run dev
