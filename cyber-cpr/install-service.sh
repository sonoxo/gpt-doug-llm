#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Cyber CPR LaunchAgent installer is for macOS. Use your OS service manager on Linux."
  exit 2
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: bash install-service.sh owner/repo [owner/repo ...]"
  exit 2
fi

BIN="${HOME}/.local/bin/cyber-cpr"
if [[ ! -x "${BIN}" ]]; then
  echo "Cyber CPR CLI not found at ${BIN}. Run bash install.sh first."
  exit 2
fi

GH_BIN="$(command -v gh || true)"
if [[ -z "${GH_BIN}" ]]; then
  echo "GitHub CLI (gh) was not found. Install/authenticate gh before installing the watch service."
  exit 2
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. Run 'gh auth login' before installing the watch service."
  exit 2
fi

LABEL="com.sonoxo.cyber-cpr"
AGENT_DIR="${HOME}/Library/LaunchAgents"
PLIST="${AGENT_DIR}/${LABEL}.plist"
LOG_DIR="${HOME}/.cyber-cpr"
SERVICE_PATH="${HOME}/.local/bin:$(dirname "${GH_BIN}"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p "${AGENT_DIR}" "${LOG_DIR}"

ARGS=""
for repo in "$@"; do
  ARGS="${ARGS}    <string>${repo}</string>\n"
done

cat > "${PLIST}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${BIN}</string>
    <string>watch</string>
$(printf "%b" "${ARGS}")    <string>--interval</string>
    <string>180</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>${SERVICE_PATH}</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>${LOG_DIR}/service.log</string>
  <key>StandardErrorPath</key><string>${LOG_DIR}/service.err.log</string>
</dict>
</plist>
EOF

plutil -lint "${PLIST}" >/dev/null
launchctl bootout "gui/$(id -u)" "${PLIST}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${PLIST}"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "🚑 Cyber CPR background service installed"
echo "   Pulse: 180 seconds"
echo "   GitHub CLI: ${GH_BIN}"
echo "   Plist: ${PLIST}"
echo "   Logs: ${LOG_DIR}/service.log"
