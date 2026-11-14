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

doctor() {
  if ! command -v ollama >/dev/null 2>&1; then
    echo "CL1: Ollama is not installed. Install the open-source runtime locally." >&2
    return 1
  fi
  if ! python3 - <<'PY'
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
  doctor) doctor ;;
  run)
    doctor
    echo "CL1 SWARM: localhost-only XUNIA web UI at http://127.0.0.1:${PORT:-8787}"
    # Module invocation keeps the repository root importable for doug_core/web.
    exec python3 -m web.xunia_server
    ;;
  *)
    echo "Usage: bash scripts/cl1-free-swarm.sh {doctor|run}" >&2
    exit 2
    ;;
esac
