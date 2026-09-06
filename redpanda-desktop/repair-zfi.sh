#!/usr/bin/env bash
set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/redpanda-desktop"
MARKER=".gpt-redpanda-node"
TARGET="${1:-auto}"
HOST_STATE="$HOME/.local/state/gpt-redpanda"
ZFI_PID="$HOST_STATE/zfi.pid"

find_usb() {
  if [[ "$TARGET" != "auto" ]]; then
    printf '%s\n' "$TARGET"
    return 0
  fi
  local p matches=()
  for p in /Volumes/*; do
    [[ -f "$p/$MARKER" ]] || continue
    matches+=("$p")
  done
  if (( ${#matches[@]} == 1 )); then
    printf '%s\n' "${matches[0]}"
    return 0
  fi
  echo "Could not uniquely identify the GPT-REDPANDA USB node." >&2
  echo "Run: bash repair-zfi.sh /Volumes/YOUR_USB_NAME" >&2
  exit 2
}

USB="$(find_usb)"
NODE="$USB/GPT-REDPANDA"
[[ -d "$NODE" && -w "$NODE" && -f "$USB/$MARKER" ]] || {
  echo "Invalid or unmounted GPT-REDPANDA node: $USB" >&2
  exit 2
}

mkdir -p "$HOST_STATE"
TMP="$(mktemp "${TMPDIR:-/tmp}/zfi_agent.XXXXXX.py")"
trap 'rm -f "$TMP"' EXIT

printf '🐼 Refreshing ZFI runtime on %s\n' "$USB"
curl -fsSL "$RAW_BASE/zfi_agent.py" -o "$TMP"

if grep -Eq '(^|[[:space:]])(from[[:space:]]+cgi[[:space:]]+import|import[[:space:]]+cgi)' "$TMP"; then
  echo "❌ Refusing stale ZFI runtime: deprecated cgi dependency still present." >&2
  exit 1
fi

PYTHON_BIN="$(command -v python3 || true)"
[[ -n "$PYTHON_BIN" ]] || { echo "python3 is required" >&2; exit 2; }
"$PYTHON_BIN" -m py_compile "$TMP"

install -m 0755 "$TMP" "$NODE/zfi_agent.py"

if [[ -f "$ZFI_PID" ]]; then
  PID="$(cat "$ZFI_PID" 2>/dev/null || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID" >/dev/null 2>&1 || true
    sleep 1
  fi
  rm -f "$ZFI_PID"
fi

printf '✅ ZFI runtime refreshed and Python-compatible\n'
printf '   Runtime: %s\n' "$NODE/zfi_agent.py"
printf '   Python: %s\n' "$($PYTHON_BIN --version 2>&1)"

if command -v redpanda-node >/dev/null 2>&1; then
  echo "📁 Opening ZYRA File Intelligence..."
  exec redpanda-node files
else
  echo "Run: ~/.local/bin/redpanda-node files"
fi
