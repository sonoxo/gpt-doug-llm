#!/usr/bin/env bash
# GPT-DOUG Motion-1 // safe, one-command Mac bootstrap.
# Preserves all existing folders. Only creates/updates its own verified checkout.
set -euo pipefail

URL="https://github.com/sonoxo/gpt-doug-llm.git"
BASE="$HOME/GPT-DOUG-Motion1"
DEST=""

command -v git >/dev/null 2>&1 || { echo "Git missing. Install Apple's free Command Line Tools using: xcode-select --install" >&2; exit 2; }

verified_checkout() {
  local folder="$1" remote top
  [[ -d "$folder/.git" ]] || return 1
  top="$(git -C "$folder" rev-parse --show-toplevel 2>/dev/null)" || return 1
  [[ "$top" == "$folder" ]] || return 1
  remote="$(git -C "$folder" remote get-url origin 2>/dev/null)" || return 1
  [[ "$remote" == "$URL" || "$remote" == "https://github.com/sonoxo/gpt-doug-llm" ]] || return 1
  return 0
}

# Never touch ~/gpt-doug-llm: it may be a user-owned non-Git directory.
if verified_checkout "$BASE"; then
  echo "Using existing verified Motion-1 checkout: $BASE"
  if git -C "$BASE" pull --ff-only; then
    DEST="$BASE"
  else
    echo "Existing checkout has local changes or cannot fast-forward. Preserving it."
  fi
fi

if [[ -z "$DEST" ]]; then
  for candidate in "$BASE" "$HOME/GPT-DOUG-Motion1-clean" "$HOME/GPT-DOUG-Motion1-2" "$HOME/GPT-DOUG-Motion1-3"; do
    if [[ -e "$candidate" || -L "$candidate" ]]; then
      continue
    fi
    echo "Cloning only Motion-1 files to: $candidate"
    git clone --depth 1 --filter=blob:none --sparse "$URL" "$candidate" || {
      echo "Clone failed. Existing folders have not been modified." >&2
      exit 2
    }
    git -C "$candidate" sparse-checkout set open_video_model docs/motion-1
    DEST="$candidate"
    break
  done
fi

if [[ -z "$DEST" ]]; then
  echo "All safe checkout paths are occupied. Nothing was overwritten." >&2
  exit 2
fi

if [[ ! -f "$DEST/open_video_model/run_mac.sh" || ! -f "$DEST/docs/motion-1/index.html" ]]; then
  echo "The repository did not provide the required studio files." >&2
  exit 2
fi

echo "GPT-DOUG Motion-1 source: $DEST"
echo "The original ~/gpt-doug-llm directory remains untouched."
cd "$DEST"
exec bash open_video_model/run_mac.sh
