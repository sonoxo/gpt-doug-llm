#!/usr/bin/env bash
set -euo pipefail

TARGET="${HOME}/.local/bin/cyber-cpr"
APP_DIR="${HOME}/.local/share/cyber-cpr"

if [[ -f "${TARGET}" ]]; then
  rm -f "${TARGET}"
  echo "🚑 Cyber CPR launcher removed from ${TARGET}"
else
  echo "Cyber CPR launcher was not installed at ${TARGET}"
fi

if [[ -d "${APP_DIR}" ]]; then
  rm -rf "${APP_DIR}"
  echo "Cyber CPR engine removed from ${APP_DIR}"
fi

echo "Heartbeat history remains at ~/.cyber-cpr. Remove that directory manually if you also want to delete state."
