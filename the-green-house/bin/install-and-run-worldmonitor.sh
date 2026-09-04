#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/sonoxo/gpt-doug-llm.git"
TARGET="${GREEN_HOUSE_HOME:-$HOME/Downloads/gpt-doug-llm}"

printf '\n🌿 THE GREEN HOUSE — universal bootstrap\n'
printf '   target: %s\n\n' "$TARGET"

if [ -d "$TARGET/.git" ]; then
  printf '🔄 Updating existing gpt-doug-llm checkout...\n'
  git -C "$TARGET" fetch origin main
  git -C "$TARGET" pull --ff-only origin main
else
  printf '📥 Cloning gpt-doug-llm with Green House source...\n'
  mkdir -p "$(dirname "$TARGET")"
  git clone --recurse-submodules "$REPO_URL" "$TARGET"
fi

git -C "$TARGET" submodule sync --recursive
git -C "$TARGET" submodule update --init --recursive

exec bash "$TARGET/the-green-house/bin/run-worldmonitor.sh"
