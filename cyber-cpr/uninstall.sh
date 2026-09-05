#!/usr/bin/env bash
set -euo pipefail

TARGET="${HOME}/.local/bin/cyber-cpr"

if [[ -f "${TARGET}" ]]; then
  rm -f "${TARGET}"
  echo "🚑 Cyber CPR launcher removed from ${TARGET}"
else
  echo "Cyber CPR launcher was not installed at ${TARGET}"
fi

echo "State remains at ~/.cyber-cpr. Remove it manually if you also want to delete heartbeat history."
