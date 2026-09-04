#!/bin/bash
set -euo pipefail

STATE_DIR="$HOME/.blackhouse-autonomy"
REPO="${BLACKHOUSE_AUTONOMY_REPO:-$STATE_DIR/repo}"
BRANCH="feature/worldmonitor-convergence-adapter-20260904"
CONFIG_DIR="$HOME/.config/blackhouse"
SECRETS_FILE="$CONFIG_DIR/secrets.env"
VENV="$STATE_DIR/venv"
PLIST="$HOME/Library/LaunchAgents/com.sonoxo.blackhouse.autonomy.plist"
LABEL="com.sonoxo.blackhouse.autonomy"

printf '\n🧠 BLACK HOUSE AUTONOMY INSTALLER\n'
printf '=================================\n'

mkdir -p "$STATE_DIR" "$CONFIG_DIR" "$HOME/Library/LaunchAgents"
chmod 700 "$STATE_DIR" "$CONFIG_DIR"

if [ ! -d "$REPO/.git" ]; then
  printf '📦 Creating isolated Black House managed clone...\n'
  git clone https://github.com/sonoxo/gpt-doug-llm.git "$REPO"
fi

printf '🔄 Loading autonomous control branch...\n'
git -C "$REPO" fetch origin "$BRANCH"
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" checkout "$BRANCH"
else
  git -C "$REPO" checkout -b "$BRANCH" "origin/$BRANCH"
fi
git -C "$REPO" pull --ff-only origin "$BRANCH"

printf '🐍 Preparing isolated Python runtime...\n'
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip pytest

if [ ! -f "$SECRETS_FILE" ] || ! grep -q '^WORLDMONITOR_API_KEY=' "$SECRETS_FILE"; then
  printf '\n🔐 Paste your WorldMonitor API key here. It stays ONLY on this Mac.\n'
  printf 'WorldMonitor key (wm_...): '
  IFS= read -r -s WM_KEY
  printf '\n'
  if [ -z "$WM_KEY" ]; then
    printf '⚠️  No key entered. Autonomy will install, but WorldMonitor will remain stopped until a key is added.\n'
  else
    umask 077
    printf 'WORLDMONITOR_API_KEY=%s\n' "$WM_KEY" > "$SECRETS_FILE"
    chmod 600 "$SECRETS_FILE"
    unset WM_KEY
    printf '✅ Key stored locally at ~/.config/blackhouse/secrets.env\n'
  fi
else
  chmod 600 "$SECRETS_FILE"
  printf '🔐 Existing local WorldMonitor key found.\n'
fi

PYTHON="$VENV/bin/python"
RUNNER="$REPO/blackhouse_autonomy/runner.py"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$RUNNER</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>BLACKHOUSE_REPO</key>
    <string>$REPO</string>
    <key>BLACKHOUSE_STATE_DIR</key>
    <string>$STATE_DIR</string>
    <key>BLACKHOUSE_CONTROL_REF</key>
    <string>origin/$BRANCH</string>
    <key>BLACKHOUSE_CONTROL_PATH</key>
    <string>ops/autonomy/control.json</string>
    <key>BLACKHOUSE_POLL_SECONDS</key>
    <string>30</string>
    <key>BLACKHOUSE_SECRETS_FILE</key>
    <string>$SECRETS_FILE</string>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>$STATE_DIR/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$STATE_DIR/launchd.err.log</string>
</dict>
</plist>
PLIST

printf '⚙️  Installing persistent LaunchAgent...\n'
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
if ! launchctl bootstrap "gui/$(id -u)" "$PLIST"; then
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  launchctl load "$PLIST"
fi
launchctl enable "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

sleep 2
printf '\n✅ BLACK HOUSE AUTONOMY IS INSTALLED\n'
printf 'Managed repo: %s\n' "$REPO"
printf 'Your normal coding checkout is untouched.\n'
printf 'Control: origin/%s:ops/autonomy/control.json\n' "$BRANCH"
printf 'Runner log: %s/runner.log\n' "$STATE_DIR"
printf 'State: %s/state.json\n' "$STATE_DIR"
printf 'WorldMonitor: http://127.0.0.1:8787/v1/intelligence/convergence?region=MENA&time_window=6h\n'
printf '\nStatus now:\n'
if [ -f "$STATE_DIR/state.json" ]; then
  cat "$STATE_DIR/state.json"
else
  printf 'Runner is starting. Check %s/runner.log\n' "$STATE_DIR"
fi
printf '\n'
