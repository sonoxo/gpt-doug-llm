#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VENV_DIR="${SHAGGOTH_VENV_DIR:-$HOME/.local/share/gpt-doug-shaggoth/venv}"
BIN_DIR="${SHAGGOTH_BIN_DIR:-$HOME/.local/bin}"
SHELL_RC="${ZDOTDIR:-$HOME}/.zshrc"

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required" >&2
  exit 1
}

mkdir -p "$(dirname "$VENV_DIR")" "$BIN_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$VENV_DIR/bin/python" -m pip install -e "${PROJECT_DIR}[api]"
ln -sf "$VENV_DIR/bin/shaggoth" "$BIN_DIR/shaggoth"

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
if [ ! -f "$SHELL_RC" ] || ! grep -Fqx "$PATH_LINE" "$SHELL_RC"; then
  printf '\n%s\n' "$PATH_LINE" >> "$SHELL_RC"
fi

export PATH="$BIN_DIR:$PATH"
hash -r 2>/dev/null || true

echo "installed: $(command -v shaggoth)"
shaggoth heartbeat
