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
mkdir -p "$LOGS" "$STATE" "$POCKET/models" "$POCKET/cache" "$POCKET/memory" "$POCKET/workspace" "$POCKET/tmp"

export LLAMA_CACHE="${LLAMA_CACHE:-$POCKET/models}"
export HF_HOME="${HF_HOME:-$POCKET/models/huggingface}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$POCKET/cache}"
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-$POCKET/cache/pycache}"
export TMPDIR="${TMPDIR:-$POCKET/tmp}"
export GPT_DOUG_API="http://127.0.0.1:${PORT}/v1"
export GPT_DOUG_POCKET="$POCKET"
export GPT_DOUG_MEMORY="${GPT_DOUG_MEMORY:-$POCKET/memory}"
export GPT_DOUG_WORKSPACE="${GPT_DOUG_WORKSPACE:-$POCKET/workspace}"

say() { printf '%s\n' "$*"; }
health() { curl -fsS --max-time 3 "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; }

pid_alive() {
  [[ -f "$PIDFILE" ]] || return 1
  local pid
  pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1
}

owned_server() {
  pid_alive || return 1
  local pid cmd
  pid="$(cat "$PIDFILE")"
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$cmd" == *"llama"* && "$cmd" == *"$PORT"* ]]
}

port_pid() {
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true
}

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
    if owned_server; then
      say "✅ GPT-DOUG POCKET server already healthy on :$PORT"
      say "💾 Pocket-owned model/cache: $LLAMA_CACHE"
      return 0
    fi
    local foreign_pid
    foreign_pid="$(port_pid)"
    say "⚠️ Port $PORT is healthy but is not owned by GPT-DOUG POCKET."
    [[ -n "$foreign_pid" ]] && say "   Listener PID: $foreign_pid"
    say "Run: \"$POCKET/gpt-doug\" takeover"
    return 4
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
    if health && owned_server; then
      say "✅ GPT-DOUG POCKET AI ONLINE"
      say "🔗 http://127.0.0.1:${PORT}/v1"
      say "💾 Model/cache: $LLAMA_CACHE"
      return 0
    fi
    sleep 2
  done
  say "❌ Model server did not become healthy."
  tail -n 40 "$LOGFILE" 2>/dev/null || true
  return 2
}

takeover() {
  local pid cmd
  pid="$(port_pid)"
  if [[ -n "$pid" ]]; then
    cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$cmd" == *"llama"* ]]; then
      say "🔄 Stopping previous llama listener PID $pid on :$PORT..."
      kill "$pid" >/dev/null 2>&1 || true
      for _ in $(seq 1 20); do
        [[ -z "$(port_pid)" ]] && break
        sleep 1
      done
    else
      say "❌ Refusing takeover: port $PORT belongs to a non-llama process."
      say "   $cmd"
      return 5
    fi
  fi
  rm -f "$PIDFILE" 2>/dev/null || true
  start_server
}

stop_server() {
  if owned_server; then
    kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true
  fi
  rm -f "$PIDFILE" 2>/dev/null || true
  say "🛑 GPT-DOUG POCKET-owned server stopped"
}

status() {
  say "=== GPT-DOUG POCKET ==="
  say "Pocket: $POCKET"
  say "Repo: $REPO"
  say "Models: $LLAMA_CACHE"
  say "Memory: $GPT_DOUG_MEMORY"
  say "Workspace: $GPT_DOUG_WORKSPACE"
  if health; then
    if owned_server; then
      say "✅ AI server healthy + POCKET OWNED :$PORT"
    else
      say "⚠️ AI server healthy but FOREIGN/LEGACY :$PORT"
    fi
  else
    say "❌ AI server offline :$PORT"
  fi
  df -h "$POCKET" | tail -n 1
}

case "${1:-chat}" in
  chat)
    start_server
    exec python3 "$REPO/zyra_pocket.py"
    ;;
  start) start_server ;;
  takeover) takeover ;;
  status) status ;;
  stop) stop_server ;;
  benchmark)
    exec python3 "$REPO/scripts/pocket-publication-benchmark.py"
    ;;
  benchmark-suite)
    exec python3 "$REPO/scripts/pocket-benchmark-suite.py"
    ;;
  sync)
    if [[ -n "$(git -C "$REPO" status --porcelain 2>/dev/null || true)" ]]; then
      say "⚠️ Repo has local changes; refusing to overwrite them."
      exit 3
    fi
    git -C "$REPO" pull --ff-only
    ;;
  *)
    say "Usage: gpt-doug {chat|start|takeover|status|stop|benchmark|benchmark-suite|sync}"
    exit 2
    ;;
esac
