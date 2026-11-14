#!/usr/bin/env bash
# CL1 / GPT-DOUG: free-only local model launcher. No paid APIs or provisioning.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export GPT_DOUG_FREE_ONLY=true
export PAID_MODE=false
export GPT_DOUG_PROVIDER=ollama
export GPT_DOUG_PROVIDER_ORDER=ollama
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:3b}"
export GPT_DOUG_ENABLE_WORKER=false

# Prefer the repository's isolated Python environment if it exists.
PYTHON_BIN="$ROOT/.venv/bin/python3"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

setup() {
  command -v python3 >/dev/null 2>&1 || {
    echo "CL1: Python 3 is required." >&2
    return 1
  }
  if [[ ! -x "$ROOT/.venv/bin/python3" ]]; then
    python3 -m venv "$ROOT/.venv"
  fi
  "$ROOT/.venv/bin/python3" -m pip install -e '.[web]'
  PYTHON_BIN="$ROOT/.venv/bin/python3"
  echo "CL1 FREE ONLY: local Python environment installed."
}

doctor() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "CL1: Ollama is not installed. Install the open-source runtime locally." >&2
    return 1
  fi
  if [[ -z "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c 'from cryptography.fernet import Fernet' >/dev/null 2>&1; then
    echo "CL1: missing Python web dependencies. Run: bash scripts/cl1-free-swarm.sh setup" >&2
    return 1
  fi
  if ! "$PYTHON_BIN" - <<'PY'
import json
import os
import urllib.error
import urllib.request

model = os.environ["OLLAMA_MODEL"]
req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"Accept": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=3) as response:
        names = [item.get("name", "") for item in json.load(response).get("models", [])]
except (OSError, ValueError, urllib.error.URLError) as exc:
    print("CL1: local Ollama is not reachable. Start `ollama serve`.", flush=True)
    raise SystemExit(1) from None
if not any(name == model or name.startswith(model + ":") for name in names):
    print(f"CL1: model {model} is not installed; run: ollama pull {model}", flush=True)
    raise SystemExit(1)
print(f"CL1 FREE ONLY: local inference ready ({model}); cloud billing disabled.")
PY
  then
    return 1
  fi
}

case "${1:-doctor}" in
  setup) setup ;;
  doctor) doctor ;;
  run)
    doctor
    echo "CL1 SWARM: localhost-only XUNIA web UI at http://127.0.0.1:${PORT:-8787}"
    # Module invocation keeps the repository root importable for doug_core/web.
    exec "$PYTHON_BIN" -m web.xunia_server
    ;;
  *)
    echo "Usage: bash scripts/cl1-free-swarm.sh {setup|doctor|run}" >&2
    exit 2
    ;;
esac
