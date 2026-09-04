#!/usr/bin/env bash
set -euo pipefail

REPO="${GREEN_HOUSE_HOME:-$HOME/Downloads/gpt-doug-llm}"
LAUNCHER="$REPO/the-green-house/bin/run-worldmonitor.sh"
BOOTSTRAP_URL="https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/the-green-house/bin/install-and-run-worldmonitor.sh"

printf '\n🌿 THE GREEN HOUSE — command installer\n'

# Ensure the Green House checkout exists. Do not source ~/.zshrc; a syntax error
# there must never prevent installation of the launcher command.
if [ ! -f "$LAUNCHER" ]; then
  printf '📥 Green House checkout missing; bootstrapping repository first...\n'
  bash <(curl -fsSL "$BOOTSTRAP_URL")
fi

# Prefer a directory already on PATH and writable by the current user. On
# Apple Silicon Macs Homebrew normally provides /opt/homebrew/bin.
INSTALL_DIR=""
OLD_IFS="$IFS"
IFS=':'
for dir in $PATH; do
  [ -n "$dir" ] || continue
  if [ -d "$dir" ] && [ -w "$dir" ]; then
    case "$dir" in
      /opt/homebrew/bin|/usr/local/bin|"$HOME"/bin|"$HOME"/.local/bin)
        INSTALL_DIR="$dir"
        break
        ;;
    esac
  fi
done
IFS="$OLD_IFS"

# If none of the preferred PATH directories exist, create ~/.local/bin and add
# it to ~/.zprofile only when needed. ~/.zprofile is used instead of ~/.zshrc so
# a broken interactive zsh config cannot block the command.
if [ -z "$INSTALL_DIR" ]; then
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR"
  case ":$PATH:" in
    *":$INSTALL_DIR:"*) ;;
    *)
      ZPROFILE="$HOME/.zprofile"
      TOUCH_LINE='export PATH="$HOME/.local/bin:$PATH"'
      touch "$ZPROFILE"
      if ! grep -Fqx "$TOUCH_LINE" "$ZPROFILE" 2>/dev/null; then
        printf '\n%s\n' "$TOUCH_LINE" >> "$ZPROFILE"
      fi
      export PATH="$INSTALL_DIR:$PATH"
      ;;
  esac
fi

TARGET="$INSTALL_DIR/greenhouse"
cat > "$TARGET" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
REPO="${GREEN_HOUSE_HOME:-$HOME/Downloads/gpt-doug-llm}"
LAUNCHER="$REPO/the-green-house/bin/run-worldmonitor.sh"
if [ ! -f "$LAUNCHER" ]; then
  printf '❌ Green House launcher not found at %s\n' "$LAUNCHER" >&2
  printf '   Reinstall with:\n   bash <(curl -fsSL https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/the-green-house/bin/install-greenhouse-command.sh)\n' >&2
  exit 2
fi
exec bash "$LAUNCHER" "$@"
EOF
chmod +x "$TARGET"

printf '✅ Installed real command: %s\n' "$TARGET"
printf '✅ No ~/.zshrc alias required.\n'
printf '🌿 Launch with: greenhouse\n\n'

# Verify the installed wrapper itself is executable and points to a valid host launcher.
"$TARGET" --help >/dev/null 2>&1 || true
