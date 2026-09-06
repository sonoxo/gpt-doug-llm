#!/usr/bin/env bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/redpanda-desktop"
MARKER=".gpt-redpanda-node"
TARGET_ARG="${1:-auto}"

say(){ printf '%s\n' "$*"; }

choose_usb() {
  if [[ "$TARGET_ARG" != "auto" ]]; then printf '%s\n' "$TARGET_ARG"; return 0; fi
  if [[ -n "${REDPANDA_USB_ROOT:-}" ]]; then printf '%s\n' "$REDPANDA_USB_ROOT"; return 0; fi
  local marked=() writable=() p
  for p in /Volumes/*; do
    [[ -d "$p" && -w "$p" ]] || continue
    [[ "$p" == "/Volumes/Macintosh HD" ]] && continue
    if [[ -f "$p/$MARKER" ]]; then marked+=("$p"); else writable+=("$p"); fi
  done
  if (( ${#marked[@]} == 1 )); then printf '%s\n' "${marked[0]}"; return 0; fi
  if (( ${#marked[@]} > 1 )); then say "Multiple GPT-REDPANDA USB nodes found:" >&2; printf '  %s\n' "${marked[@]}" >&2; exit 2; fi
  if (( ${#writable[@]} == 1 )); then printf '%s\n' "${writable[0]}"; return 0; fi
  say "Could not safely auto-select one USB volume." >&2
  say "Run: bash install.sh /Volumes/YOUR_USB_NAME" >&2
  if (( ${#writable[@]} )); then printf '  candidate: %s\n' "${writable[@]}" >&2; fi
  exit 2
}

if [[ "$(uname -s)" != "Darwin" ]]; then say "This installer currently targets macOS."; exit 2; fi
USB="$(choose_usb)"
[[ -d "$USB" && -w "$USB" ]] || { say "USB path is not writable: $USB"; exit 2; }

NODE="$USB/GPT-REDPANDA"
STATE="$USB/.redpanda"
HOST_SHARE="$HOME/.local/share/gpt-redpanda"
HOST_STATE="$HOME/.local/state/gpt-redpanda"
HOST_BIN="$HOME/.local/bin"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
PLIST="$LAUNCH_DIR/com.sonoxo.gpt-redpanda.plist"
LABEL="com.sonoxo.gpt-redpanda"

say "🐼 Installing GPT-REDPANDA-LLM / GPT-DOUG-LLM runtime to: $USB"
mkdir -p "$NODE" "$STATE/logs" "$STATE/memory" "$STATE/events" "$STATE/zfi" "$HOST_SHARE" "$HOST_STATE" "$HOST_BIN" "$LAUNCH_DIR"
printf 'GPT-REDPANDA-LLM USB NODE\nCORE=GPT-DOUG-LLM\n' > "$USB/$MARKER"

fetch() { local name="$1"; curl -fsSL "$REPO_RAW/$name" -o "$NODE/$name"; }
fetch redpanda_agent.py
fetch gpt_redpanda_llm.py
fetch agentic_cpr_runtime.py
fetch zfi_agent.py
fetch redpanda-zsh-hook.zsh
fetch redpanda-node
chmod +x "$NODE/redpanda_agent.py" "$NODE/gpt_redpanda_llm.py" "$NODE/agentic_cpr_runtime.py" "$NODE/zfi_agent.py" "$NODE/redpanda-node"

cp "$NODE/redpanda-node" "$HOST_BIN/redpanda-node"
chmod +x "$HOST_BIN/redpanda-node"
cp "$NODE/redpanda-zsh-hook.zsh" "$HOST_SHARE/redpanda-zsh-hook.zsh"

EVENT_FILE="$STATE/events/terminal-events.tsv"
touch "$EVENT_FILE"
cat > "$HOST_SHARE/env.zsh" <<'EOF'
unset REDPANDA_USB_ROOT REDPANDA_EVENT_FILE
for _redpanda_volume in /Volumes/*; do
  [[ -f "$_redpanda_volume/.gpt-redpanda-node" ]] || continue
  export REDPANDA_USB_ROOT="$_redpanda_volume"
  export REDPANDA_EVENT_FILE="$_redpanda_volume/.redpanda/events/terminal-events.tsv"
  break
done
unset _redpanda_volume
[[ -n "${REDPANDA_EVENT_FILE:-}" && -f "$HOME/.local/share/gpt-redpanda/redpanda-zsh-hook.zsh" ]] && source "$HOME/.local/share/gpt-redpanda/redpanda-zsh-hook.zsh"
EOF

touch "$HOME/.zshenv"
HOOK_LINE='[[ -f "$HOME/.local/share/gpt-redpanda/env.zsh" ]] && source "$HOME/.local/share/gpt-redpanda/env.zsh"'
grep -qxF "$HOOK_LINE" "$HOME/.zshenv" || printf '\n%s\n' "$HOOK_LINE" >> "$HOME/.zshenv"
if [[ ! -f "$STATE/cyber-cpr-config.json" ]]; then printf '{\n  "repairs": []\n}\n' > "$STATE/cyber-cpr-config.json"; fi

SERVICE_PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
HOST_OUT="$HOST_STATE/launchd.log"
HOST_ERR="$HOST_STATE/launchd.err.log"
: > "$HOST_OUT"; : > "$HOST_ERR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$HOST_BIN/redpanda-node</string><string>run</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$SERVICE_PATH</string>
    <key>REDPANDA_USB_ROOT</key><string>$USB</string>
    <key>REDPANDA_EVENT_FILE</key><string>$EVENT_FILE</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$HOST_OUT</string>
  <key>StandardErrorPath</key><string>$HOST_ERR</string>
</dict></plist>
EOF

plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
grep -qxF "$PATH_LINE" "$HOME/.zshenv" || printf '%s\n' "$PATH_LINE" >> "$HOME/.zshenv"
export PATH="$HOME/.local/bin:$PATH"

sleep 3
say ""
if lsof -nP -iTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then say "✅ GPT-REDPANDA-LLM merged runtime is LIVE"; else
  say "⚠️ GPT-REDPANDA-LLM installed, but the portal is not listening yet."
  launchctl print "gui/$(id -u)/${LABEL}" 2>/dev/null | grep -E 'state =|pid =|last exit code|job state' || true
  [[ -s "$HOST_ERR" ]] && { say "--- launchd stderr ---"; tail -n 20 "$HOST_ERR" || true; }
  [[ -s "$HOST_OUT" ]] && { say "--- launchd stdout ---"; tail -n 20 "$HOST_OUT" || true; }
fi
say "🧠 Core: GPT-DOUG-LLM"
say "🐼 Runtime: GPT-REDPANDA-LLM"
say "🤖 Agentic CPR: autonomous + bounded + verify + circuit breaker"
say "💾 Node: $NODE"
say "🧬 State: $STATE"
say "🚑 Cyber CPR: $(command -v cyber-cpr || echo 'install cyber-cpr separately')"
say "👁 Terminal watch: metadata only (exit status + cwd; no command text)"
say "🖥 Desktop: redpanda-node open"
say "📁 ZFI Files: redpanda-node files"
say "🤖 Agentic CPR state: redpanda-node agentic-cpr-status"
say "📱 Mobile/LAN: redpanda-node mobile"
say "🔎 Status: redpanda-node status"
say "🚑 Manual CPR: redpanda-node cpr"
say ""
say "Open the portal with: redpanda-node open"
