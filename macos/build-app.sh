#!/usr/bin/env bash
# Build a native macOS .app from local SwiftUI sources, pointing at this
# checkout's existing .venv. No network install, API token or paid service.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
PACKAGE="$SCRIPT_DIR/SkullOS"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
APP_DEST="$REPO_ROOT/dist"
APP_PATH="$APP_DEST/SKULL OS.app"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Build requires macOS 13+ with Xcode Command Line Tools." >&2
  exit 2
fi
if ! command -v swift >/dev/null 2>&1; then
  echo "Swift is missing. Install Apple's Xcode Command Line Tools: xcode-select --install" >&2
  exit 2
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing local virtual environment. From repository root run:" >&2
  echo "python3 -m venv .venv && .venv/bin/python -m pip install -e ." >&2
  exit 2
fi
if ! "$VENV_PYTHON" -c 'from skull_llm.server import serve' >/dev/null 2>&1; then
  echo "Your .venv does not contain SKULL-LLM. Run: .venv/bin/python -m pip install -e ." >&2
  exit 2
fi

swift build --package-path "$PACKAGE" --configuration release
BIN_DIR="$(swift build --package-path "$PACKAGE" --configuration release --show-bin-path)"
mkdir -p "$APP_DEST"
STAGING="$(mktemp -d "$APP_DEST/.skullos.XXXXXX")"
trap 'rm -rf "$STAGING"' EXIT
BUNDLE="$STAGING/SKULL OS.app"
mkdir -p "$BUNDLE/Contents/MacOS" "$BUNDLE/Contents/Resources"
cp "$BIN_DIR/SkullOS" "$BUNDLE/Contents/MacOS/SkullOS"
chmod 755 "$BUNDLE/Contents/MacOS/SkullOS"
cp "$PACKAGE/Info.plist" "$BUNDLE/Contents/Info.plist"
SKULL_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
"$VENV_PYTHON" - "$BUNDLE/Contents/Resources/SkullConfig.json" "$VENV_PYTHON" "$REPO_ROOT" "$SKULL_MODEL" <<'PY'
import json
import sys
output, python_path, root, model = sys.argv[1:]
with open(output, 'w', encoding='utf-8') as stream:
    json.dump({
        'pythonExecutable': python_path,
        'repositoryRoot': root,
        'defaultModel': model,
        'port': 7861,
    }, stream, indent=2)
PY
# An ad-hoc local signature is not notarization, and is not a distribution ID.
codesign --force --sign - "$BUNDLE" >/dev/null
if [[ -e "$APP_PATH" ]]; then
  BACKUP="$APP_DEST/SKULL OS.previous-$(date +%Y%m%d-%H%M%S).app"
  if [[ -e "$BACKUP" ]]; then
    echo "Backup already exists, refusing to replace: $BACKUP" >&2
    exit 2
  fi
  mv "$APP_PATH" "$BACKUP"
  echo "Previous app preserved: $BACKUP"
fi
mv "$BUNDLE" "$APP_PATH"
echo "Built: $APP_PATH"
echo "Launch: open '$APP_PATH'"
if [[ "${1:-}" == "--open" ]]; then
  open "$APP_PATH"
fi
