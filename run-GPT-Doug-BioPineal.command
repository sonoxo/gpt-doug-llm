#!/usr/bin/env bash
# GPT-Doug BioPineal evidence nexus: free, local, no chemical actuators.
set -euo pipefail
ROOT="$(cd "$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
MODE="\${1:-open}"
case "$MODE" in
  open)
    bash "$ROOT/scripts/doug-max" bio-pineal audit >/dev/null
    bash "$ROOT/scripts/doug-max" bio-pineal map
    OUTDIR="$(mktemp -d "\${TMPDIR:-/tmp}/gpt-doug-biopineal.XXXXXXXX")"
    bash "$ROOT/scripts/doug-max" bio-pineal html >"$OUTDIR/biopineal.html"
    echo "BioPineal local report: $OUTDIR/biopineal.html"
    if command -v open >/dev/null 2>&1; then
      open "$OUTDIR/biopineal.html"
    else
      echo "Open the local HTML file in a browser to see the visual dashboard."
    fi
    ;;
  watch)
    shift
    exec bash "$ROOT/scripts/doug-max" bio-pineal watch "$@"
    ;;
  *)
    echo "Usage: bash run-GPT-Doug-BioPineal.command [open|watch --frames N --interval S]" >&2
    exit 2
    ;;
esac
