#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/platform_one/repo1-qbio"
DEST="${1:-$ROOT/repo1-qbio-export}"

if [ -e "$DEST" ]; then
  printf '%s\n' "Refusing to overwrite existing destination: $DEST" >&2
  exit 2
fi

mkdir -p "$DEST"
cp -R "$SOURCE"/. "$DEST"/

printf '%s\n' "Repo One standalone project exported to: $DEST"
printf '%s\n' "Next: replace hardening_manifest.yaml maintainer placeholders before submission."
