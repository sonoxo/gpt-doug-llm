#!/usr/bin/env bash
set -euo pipefail

# ZYRA CPR — zero-cost local recovery/bootstrap for macOS.
# GitHub is the recovery/distribution plane; compute stays on your machine.

ROOT="${HOME}/.zyra-zero-cloud"
PORT="${ZYRA_PORT:-9931}"
MODEL="${ZYRA_MODEL:-ggml-org/Qwen3-4B-GGUF:Q4_K_M}"
REMOTE_URL="${ZYRA_WORKER_URL:-}"
LOG="$ROOT/worker.log"
PIDFILE="$ROOT/worker.pid"
STATE="$ROOT/runtime.json"
mkdir -p "$ROOT"

say() { printf '%s\n' "$*"; }
health() { curl -fsS --max-time 3 "$1/health" >/dev/null 2>&1 || curl -fsS --max-time 3 "$1/v1/models" >/dev/null 2>&1; }
local_url() { printf 'http://127.0.0.1:%s' "$PORT"; }
lan_ip() { ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || printf '127.0.0.1'; }

write_state() {
  local mode="$1" url="$2" status="$3"
  cat > "$STATE" <<EOF
{
  "system": "Zyra Cloud / NXYZ",
  "recovery": "CPR",
  "mode": "$mode",
  "status": "$status",
  "url": "$url",
  "hostname": "$(hostname)",
  "architecture": "$(uname -m)",
  "timestamp_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

ensure_llama() {
  if command -v llama-server >/dev/null 2>&1; then return 0; fi
  if ! command -v brew >/dev/null 2>&1; then
    say "❌ Homebrew is missing. Install Homebrew, then rerun CPR."
    exit 10
  fi
  say "🧰 CPR installing llama.cpp..."
  brew install llama.cpp
}

start_local() {
  ensure_llama
  if health "$(local_url)"; then
    say "✅ Local worker already healthy: $(local_url)"
    write_state "LOCAL" "$(local_url)" "HEALTHY"
    return 0
  fi

  if [[ -f "$PIDFILE" ]]; then kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true; fi
  pkill -f "llama-server.*--port ${PORT}" >/dev/null 2>&1 || true

  say "🫀 CPR starting local worker on port $PORT..."
  nohup llama-server \
    -hf "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    -c 4096 \
    >"$LOG" 2>&1 &
  echo $! > "$PIDFILE"

  for _ in $(seq 1 60); do
    if health "$(local_url)"; then
      local ip
      ip="$(lan_ip)"
      write_state "LOCAL" "http://${ip}:${PORT}" "HEALTHY"
      say "✅ CPR RECOVERED"
      say "🌐 Local: $(local_url)"
      say "🌐 LAN:   http://${ip}:${PORT}"
      say "🔗 API:   http://${ip}:${PORT}/v1"
      return 0
    fi
    sleep 2
  done

  write_state "LOCAL" "$(local_url)" "FAILED"
  say "❌ Local worker did not become healthy."
  say "📜 tail -n 80 '$LOG'"
  exit 20
}

heal() {
  say "🚑 ZYRA CPR"

  # 1. Prefer a configured remote worker when healthy.
  if [[ -n "$REMOTE_URL" ]]; then
    say "🔎 Checking configured worker: $REMOTE_URL"
    if health "$REMOTE_URL"; then
      write_state "REMOTE" "$REMOTE_URL" "HEALTHY"
      say "✅ Remote worker healthy. No fallback needed."
      return 0
    fi
    say "⚠️ Remote worker unreachable — activating zero-cost local fallback."
  fi

  # 2. Reuse an already-running local worker.
  if health "$(local_url)"; then
    write_state "LOCAL" "$(local_url)" "HEALTHY"
    say "✅ Local worker healthy: $(local_url)"
    return 0
  fi

  # 3. On Apple Silicon, automatically resurrect the inference worker.
  if [[ "$(uname -m)" == "arm64" ]]; then
    start_local
    return 0
  fi

  # 4. Intel/control nodes do not download a 4B model by default.
  write_state "CONTROL_ONLY" "${REMOTE_URL:-none}" "DEGRADED"
  say "⚠️ Intel/control node is healthy but no AI worker is reachable."
  say "Run CPR on the M2 first, then set:"
  say "export ZYRA_WORKER_URL=http://<M2-IP>:${PORT}"
  say "./scripts/zyra-cpr.sh heal"
  exit 30
}

status() {
  say "=== ZYRA CPR STATUS ==="
  [[ -f "$STATE" ]] && cat "$STATE" || say "No runtime state yet."
  if health "$(local_url)"; then say "✅ localhost:$PORT healthy"; else say "❌ localhost:$PORT not healthy"; fi
  [[ -n "$REMOTE_URL" ]] && { health "$REMOTE_URL" && say "✅ remote healthy: $REMOTE_URL" || say "❌ remote unavailable: $REMOTE_URL"; }
}

stop() {
  [[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true
  rm -f "$PIDFILE"
  pkill -f "llama-server.*--port ${PORT}" >/dev/null 2>&1 || true
  say "🛑 ZYRA worker stopped"
}

case "${1:-heal}" in
  heal) heal ;;
  start) start_local ;;
  status) status ;;
  stop) stop ;;
  *) say "Usage: $0 {heal|start|status|stop}"; exit 2 ;;
esac
