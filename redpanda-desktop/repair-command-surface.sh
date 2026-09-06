#!/usr/bin/env bash
set -euo pipefail

RAW="https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/redpanda-desktop"
HOST_BIN="$HOME/.local/bin"
HOST_SHARE="$HOME/.local/share/gpt-redpanda"
ENV_FILE="$HOST_SHARE/env.zsh"
ZSHENV="$HOME/.zshenv"

mkdir -p "$HOST_BIN" "$HOST_SHARE"

curl -fsSL "$RAW/va3lm-cpr" -o "$HOST_BIN/va3lm-cpr"
curl -fsSL "$RAW/glass" -o "$HOST_BIN/glass"
chmod +x "$HOST_BIN/va3lm-cpr" "$HOST_BIN/glass"

# Preserve the existing Red Panda environment and add the slash-command alias.
touch "$ENV_FILE"
ALIAS_LINE="alias '/glass=glass'"
grep -qxF "$ALIAS_LINE" "$ENV_FILE" || printf '\n%s\n' "$ALIAS_LINE" >> "$ENV_FILE"

touch "$ZSHENV"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
HOOK_LINE='[[ -f "$HOME/.local/share/gpt-redpanda/env.zsh" ]] && source "$HOME/.local/share/gpt-redpanda/env.zsh"'
grep -qxF "$PATH_LINE" "$ZSHENV" || printf '%s\n' "$PATH_LINE" >> "$ZSHENV"
grep -qxF "$HOOK_LINE" "$ZSHENV" || printf '%s\n' "$HOOK_LINE" >> "$ZSHENV"

printf '✅ GPT-REDPANDA command surface repaired\n'
printf '   va3lm-cpr -> %s\n' "$HOST_BIN/va3lm-cpr"
printf '   glass     -> %s\n' "$HOST_BIN/glass"
printf '   /glass    -> zsh alias to glass (active after: source ~/.zshenv)\n'
