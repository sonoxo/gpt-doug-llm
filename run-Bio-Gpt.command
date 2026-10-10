#!/usr/bin/env bash
# Self-contained Bio-Gpt terminal startup; only Python 3.9+ required.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'BIO-GPT ERROR: Python 3 is missing. Install Python 3.9+ and rerun.' >&2
  exit 127
fi
cd "$ROOT"
if ! python3 -c 'import research_lab.bio_hilbert, research_lab.bio_gpt, research_lab.bio_gpt_terminal' 2>/dev/null; then
  printf '%s\n' 'BIO-GPT ERROR: installation incomplete (bio_hilbert.py and bio_gpt.py both required).' >&2
  exit 1
fi
exec python3 -m research_lab.bio_gpt_terminal "$@"
