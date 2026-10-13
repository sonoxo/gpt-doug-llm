#!/bin/sh
# Bootstrap GPT-Doug OSIRIS into a dedicated checkout from ANY directory.
set -eu
REPO='https://github.com/sonoxo/gpt-doug-llm.git'
BRANCH='feature/pineal-osiris-local-clone'
DEST=${GPT_DOUG_OSIRIS_HOME:-"$HOME/.local/share/gpt-doug/gpt-doug-llm-osiris"}
if [ "${1:-}" = '--check' ]; then
  command -v git >/dev/null 2>&1 || { echo 'Install git first' >&2; exit 2; }
  printf 'Bootstrap from: %s\nBranch: %s\nInstall: %s\n' "$REPO" "$BRANCH" "$DEST"
  exit 0
fi
if [ "${1:-}" != '' ] && [ "${1:-}" != 'stack' ]; then
  echo 'Usage: sh bootstrap.sh [stack|--check]' >&2; exit 2
fi
command -v git >/dev/null 2>&1 || { echo 'Missing dependency: git' >&2; exit 2; }
if [ -e "$DEST" ] && [ ! -d "$DEST/.git" ]; then
  echo "Refusing unexpected existing directory: $DEST" >&2; exit 2
fi
if [ ! -d "$DEST/.git" ]; then
  mkdir -p "$(dirname -- "$DEST")"
  git clone --depth=1 --single-branch --branch "$BRANCH" "$REPO" "$DEST"
else
  origin=$(git -C "$DEST" remote get-url origin)
  if [ "$origin" != "$REPO" ]; then
    echo "Refusing unrelated checkout: $origin" >&2; exit 2
  fi
  if [ -n "$(git -C "$DEST" status --porcelain)" ]; then
    echo 'Bootstrap checkout contains local changes; refusing to replace them' >&2; exit 2
  fi
  git -C "$DEST" fetch --depth=1 origin "$BRANCH"
  git -C "$DEST" switch -C "$BRANCH" FETCH_HEAD
fi
exec sh "$DEST/integrations/pineal_osiris/run.sh" stack
