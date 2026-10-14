#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/platform_one/repo1-hardening"
DEST="${1:-$ROOT/repo1-qbio-hardening-export}"

if [ -e "$DEST" ]; then
  printf '%s\n' "Refusing to overwrite existing destination: $DEST" >&2
  exit 2
fi

mkdir -p "$DEST"
cp -R "$SOURCE"/. "$DEST"/

printf '%s\n' "Repo One hardening-only project exported to: $DEST"
printf '%s\n' "Replace the three REPLACE_WITH_* maintainer fields before submission."
printf '%s\n' "Push to the feature branch assigned by your Repo One project; do not push directly to master."
