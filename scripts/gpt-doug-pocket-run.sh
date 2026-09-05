#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POCKET="${GPT_DOUG_POCKET:-$REPO_ROOT}"
if [[ -d "$POCKET/repo/.git" ]]; then
  REPO="$POCKET/repo"
else
  REPO="$REPO_ROOT"
fi
PORT="${ZYRA_PORT:-9931}"
MODEL="${ZYRA_MODEL:-ggml-org/Qwen3-0.6B-GGUF:Q4_0}"
LOGS="${GPT_DOUG_LOGS:-$POCKET/logs}"
STATE="${GPT_DOUG_HOME:-$POCKET/state}"
PIDFILE="$STATE/llama.pid"
LOGFILE="$LOGS/llama.log"
mkdir -p "$LOGS" "$STATE" "$POCKET/models" "$POCKET/cache" "$POCKET/memory" "$POCKET/workspace"

export LLAMA_CACHE="${LLAMA_CACHE:-$POCKET/models}"
export HF_HOME="${HF_HOME:-$POCKET/models/huggingface}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$POCKET/cache}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$POCKET/cache/pycache}"
export GPT_DOUG_API="http://127.0.0.1:${PORT}/v1"
export GPT_DOUG_POCKET="$POCKET"
export GPT_DOUG_MEMORY="${GPT_DOUG_MEMORY:-$POCKET/memory}"
export GPT_DOUG_WORKSPACE="${GPT_DOUG_WORKSPACE:-$POCKET/workspace}"

say() { printf '%s\n' "$*"; }
health() { curl -fsS --max-time 3 "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; }

resolve_runtime() {
  if command -v llama >/dev/null 2>&1; then
    RUNTIME_KIND="llama"
    RUNTIME_BIN="$(command -v llama)"
    return 0
  fi
  if command -v llama-server >/dev/null 2>&1; then
    RUNTIME_KIND="llama-server"
    RUNTIME_BIN="$(command -v llama-server)"
    return 0
  fi
  say "⚠️ llama.cpp runtime not found."
  if command -v brew >/dev/null 2>&1; then
    say "🧰 Installing free llama.cpp runtime with Homebrew..."
    brew install llama.cpp
    if command -v llama >/dev/null 2>&1; then
      RUNTIME_KIND="llama"; RUNTIME_BIN="$(command -v llama)"; return 0
    fi
    if command -v llama-server >/dev/null 2>&1; then
      RUNTIME_KIND="llama-server"; RUNTIME_BIN="$(command -v llama-server)"; return 0
    fi
  fi
  say "❌ No llama.cpp runtime available."
  say "Install free llama.cpp once, then rerun GPT-DOUG POCKET."
  return 1
}

start_server() {
  if health; then
    say "✅ Local AI server already healthy on :$PORT"
    return 0
  fi
  resolve_runtime
  if [[ -f "$PIDFILE" ]]; then kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true; fi
  rm -f "$PIDFILE" "$LOGFILE" 2>/dev/null || true

  say "🫀 Starting GPT-DOUG POCKET local model..."
  say "💾 Model/cache lives at: $LLAMA_CACHE"
  say "🧠 Model: $MODEL"

  if [[ "$RUNTIME_KIND" == "llama" ]]; then
    nohup "$RUNTIME_BIN" serve -hf "$MODEL" --host 127.0.0.1 --port "$PORT" -c 2048 >"$LOGFILE" 2>&1 &
  else
    nohup "$RUNTIME_BIN" -hf "$MODEL" --host 127.0.0.1 --port "$PORT" -c 2048 >"$LOGFILE" 2>&1 &
  fi
  printf '%s\n' "$!" > "$PIDFILE"

  for _ in $(seq 1 120); do
    if health; then
      say "✅ GPT-DOUG POCKET AI ONLINE"
      say "🔗 http://127.0.0.1:${PORT}/v1"
      return 0
    fi
    sleep 2
  done
  say "❌ Model server did not become healthy."
  tail -n 40 "$LOGFILE" 2>/dev/null || true
  return 2
}

stop_server() {
  [[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true
  rm -f "$PIDFILE" 2>/dev/null || true
  say "🛑 GPT-DOUG POCKET server stopped"
}

status() {
  say "=== GPT-DOUG POCKET ==="
  say "Pocket: $POCKET"
  say "Repo: $REPO"
  say "Models: $LLAMA_CACHE"
  say "Memory: $GPT_DOUG_MEMORY"
  say "Workspace: $GPT_DOUG_WORKSPACE"
  if health; then say "✅ AI server healthy :$PORT"; else say "❌ AI server offline :$PORT"; fi
  df -h "$POCKET" | tail -n 1
}

case "${1:-chat}" in
  chat)
    start_server
    exec python3 "$REPO/zyra_pocket.py"
    ;;
  start) start_server ;;
  status) status ;;
  stop) stop_server ;;
  sync)
    if [[ -n "$(git -C "$REPO" status --porcelain 2>/dev/null || true)" ]]; then
      say "⚠️ Repo has local changes; refusing to overwrite them."
      exit 3
    fi
    git -C "$REPO" pull --ff-only
    ;;
  *)
    say "Usage: gpt-doug {chat|start|status|stop|sync}"
    exit 2
    ;;
esac
