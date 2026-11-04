#!/usr/bin/env bash
# Safe Mac install: reuse verified Sonoxo clone, else sparse-clone a new directory.
# Never remove, overwrite or rename existing user data.
set -euo pipefail
REPO='https://github.com/sonoxo/gpt-doug-llm.git'
command -v git >/dev/null 2>&1 || { echo 'Install free Git: xcode-select --install' >&2; exit 2; }
verified() {
  [[ -d "$1/.git" ]] || return 1
  local top remote
  top="$(git -C "$1" rev-parse --show-toplevel 2>/dev/null)" || return 1
  remote="$(git -C "$1" remote get-url origin 2>/dev/null)" || return 1
  [[ "$top" == "$1" && ( "$remote" == "$REPO" || "$remote" == 'https://github.com/sonoxo/gpt-doug-llm' ) ]]
}
BASE=''
for folder in "$HOME/GPT-DOUG-Motion1" "$HOME/GPT-DOUG-Cinema" "$HOME/GPT-DOUG-Cinema-2"; do
  if verified "$folder"; then
    echo "Found verified Sonoxo checkout: $folder"
    if git -C "$folder" pull --ff-only &&
       { git -C "$folder" sparse-checkout add cinema_studio || git -C "$folder" checkout HEAD -- cinema_studio; } &&
       [[ -f "$folder/cinema_studio/run_mac.sh" ]]; then
      BASE="$folder"
      break
    fi
    echo 'Existing checkout could not be updated. Preserving it and trying a clean location.'
  fi
done
if [[ -z "$BASE" ]]; then
  for folder in "$HOME/GPT-DOUG-Cinema" "$HOME/GPT-DOUG-Cinema-2" "$HOME/GPT-DOUG-Cinema-3"; do
    [[ ! -e "$folder" && ! -L "$folder" ]] || continue
    echo "Cloning free Cinema Studio source: $folder"
    git clone --depth 1 --filter=blob:none --sparse "$REPO" "$folder"
    git -C "$folder" sparse-checkout set cinema_studio
    BASE="$folder"
    break
  done
fi
if [[ -z "$BASE" || ! -f "$BASE/cinema_studio/run_mac.sh" ]]; then
  echo 'No safe install directory available. Existing folders remain unchanged.' >&2
  exit 2
fi
cd "$BASE"
echo "GPT-DOUG CINEMA CHECKOUT: $BASE"
exec bash cinema_studio/run_mac.sh
