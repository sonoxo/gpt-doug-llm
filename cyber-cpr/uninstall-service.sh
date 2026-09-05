#!/usr/bin/env bash
set -euo pipefail

LABEL="com.sonoxo.cyber-cpr"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Cyber CPR LaunchAgent uninstaller is for macOS."
  exit 2
fi

if [[ -f "${PLIST}" ]]; then
  launchctl bootout "gui/$(id -u)" "${PLIST}" >/dev/null 2>&1 || true
  rm -f "${PLIST}"
fi

echo "Cyber CPR background service removed. CLI and state were left intact."
