#!/usr/bin/env bash
set -euo pipefail

# ZYRA CPR v2 — zero-cost local recovery/bootstrap for macOS.
# GitHub is the recovery/distribution plane; compute stays on your machine.
# CPR never deletes personal files. Its cleanup is limited to its own state/logs
# and Homebrew download/old-package cache.

ROOT="${HOME}/.zyra-zero-cloud"
PORT="${ZYRA_PORT:-9931}"
REMOTE_URL="${ZYRA_WORKER_URL:-}"
LOG="$ROOT/worker.log"
PIDFILE="$ROOT/worker.pid"
STATE="$ROOT/runtime.json"
LOW_MODEL="ggml-org/Qwen3-0.6B-GGUF:Q4_0"
NORMAL_MODEL="ggml-org/Qwen3-4B-GGUF:Q4_K_M"
mkdir -p "$ROOT" 2>/dev/null || true

say() { printf '%s\n' "$*"; }
health() { curl -fsS --max-time 3 "$1/health" >/dev/null 2>&1 || curl -fsS --max-time 3 "$1/v1/models" >/dev/null 2>&1; }
local_url() { printf 'http://127.0.0.1:%s' "$PORT"; }
lan_ip() { ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || printf '127.0.0.1'; }
free_mb() { df -Pm "$HOME" 2>/dev/null | awk 'NR==2 {print $4+0}'; }

safe_cleanup() {
  say "🧹 CPR safe cleanup: reclaiming cache space only..."
  rm -f "$LOG" "$PIDFILE" "$STATE" 2>/dev/null || true
  if command -v brew >/dev/null 2>&1; then
    brew cleanup --prune=all >/dev/null 2>&1 || true
    rm -rf "$HOME/Library/Caches/Homebrew/downloads"/* 2>/dev/null || true
  fi
}

preflight_disk() {
  local mb
  mb="$(free_mb)"
  say "💾 Free disk: ${mb} MB"

  if (( mb < 1200 )); then
    say "⚠️ Disk pressure detected — CPR cache cleanup engaged."
    safe_cleanup
    mb="$(free_mb)"
    say "💾 Free disk after cleanup: ${mb} MB"
  fi

  if (( mb < 650 )); then
    say "❌ DISK_CRITICAL: less than 650 MB free."
    say "CPR will not delete personal files. Free at least 1 GB, then rerun: ~/zyra-cpr.sh heal"
    say "Quick inspection: df -h / && du -sh ~/Downloads/* 2>/dev/null | sort -h | tail"
    exit 40
  fi
}

select_model() {
  local mb
  mb="$(free_mb)"
  if [[ -n "${ZYRA_MODEL:-}" ]]; then
    MODEL="$ZYRA_MODEL"
  elif (( mb < 5000 )); then
    MODEL="$LOW_MODEL"
  else
    MODEL="$NORMAL_MODEL"
  fi

  if [[ "$MODEL" == "$LOW_MODEL" ]]; then
    CTX="${ZYRA_CTX:-2048}"
    say "🪶 LOW-DISK mode: Qwen3 0.6B Q4_0 (~429 MB model)."
  else
    CTX="${ZYRA_CTX:-4096}"
    say "🧠 NORMAL mode: Qwen3 4B Q4_K_M."
  fi
}

write_state() {
  local mode="$1" url="$2" status="$3"
  cat > "$STATE" <<EOF
{
  "system": "Zyra Cloud / NXYZ",
  "recovery": "CPR-v2",
  "mode": "$mode",
  "status": "$status",
  "url": "$url",
  "hostname": "$(hostname)",
  "architecture": "$(uname -m)",
  "free_disk_mb": $(free_mb),
  "model": "${MODEL:-none}",
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
  preflight_disk
  say "🧰 CPR installing llama.cpp..."
  brew install llama.cpp
}

start_local() {
  preflight_disk
  ensure_llama
  select_model

  if health "$(local_url)"; then
    say "✅ Local worker already healthy: $(local_url)"
    write_state "LOCAL" "$(local_url)" "HEALTHY"
    return 0
  fi

  if [[ -f "$PIDFILE" ]]; then kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true; fi
  pkill -f "llama-server.*--port ${PORT}" >/dev/null 2>&1 || true
  rm -f "$LOG" "$PIDFILE" 2>/dev/null || true

  say "🫀 CPR starting local worker on port $PORT..."
  nohup llama-server \
    -hf "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    -c "$CTX" \
    >"$LOG" 2>&1 &
  local worker_pid=$!

  if ! printf '%s\n' "$worker_pid" > "$PIDFILE" 2>/dev/null; then
    kill "$worker_pid" >/dev/null 2>&1 || true
    say "❌ Could not write worker PID — disk is still full."
    safe_cleanup
    exit 41
  fi

  for _ in $(seq 1 90); do
    if health "$(local_url)"; then
      local ip
      ip="$(lan_ip)"
      write_state "LOCAL" "http://${ip}:${PORT}" "HEALTHY"
      say "✅ CPR RECOVERED"
      say "🌐 Local: $(local_url)"
      say "🌐 LAN:   http://${ip}:${PORT}"
      say "🔗 API:   http://${ip}:${PORT}/v1"
      say "🧠 Model: $MODEL"
      return 0
    fi
    sleep 2
  done

  write_state "LOCAL" "$(local_url)" "FAILED" 2>/dev/null || true
  say "❌ Local worker did not become healthy."
  say "📜 tail -n 80 '$LOG'"
  tail -n 25 "$LOG" 2>/dev/null || true
  exit 20
}

heal() {
  say "🚑 ZYRA CPR v2"
  preflight_disk

  # 1. Prefer a configured remote worker when healthy.
  if [[ -n "$REMOTE_URL" ]]; then
    say "🔎 Checking configured worker: $REMOTE_URL"
    if health "$REMOTE_URL"; then
      select_model
      write_state "REMOTE" "$REMOTE_URL" "HEALTHY"
      say "✅ Remote worker healthy. No fallback needed."
      return 0
    fi
    say "⚠️ Remote worker unreachable — activating zero-cost local fallback."
  fi

  # 2. Reuse an already-running local worker.
  if health "$(local_url)"; then
    select_model
    write_state "LOCAL" "$(local_url)" "HEALTHY"
    say "✅ Local worker healthy: $(local_url)"
    return 0
  fi

  # 3. Apple Silicon resurrects a compact inference worker automatically.
  if [[ "$(uname -m)" == "arm64" ]]; then
    start_local
    return 0
  fi

  # 4. Intel is control-plane only by default.
  select_model
  write_state "CONTROL_ONLY" "${REMOTE_URL:-none}" "DEGRADED" 2>/dev/null || true
  say "⚠️ Intel/control node is healthy but no AI worker is reachable."
  say "Run CPR on the M2 first, then set:"
  say "export ZYRA_WORKER_URL=http://<M2-IP>:${PORT}"
  say "~/zyra-cpr.sh heal"
  exit 30
}

doctor() {
  say "=== ZYRA CPR DOCTOR ==="
  say "Host: $(hostname)"
  say "Arch: $(uname -m)"
  say "Free disk: $(free_mb) MB"
  command -v llama-server >/dev/null 2>&1 && say "✅ llama-server installed" || say "❌ llama-server missing"
  health "$(local_url)" && say "✅ localhost:$PORT healthy" || say "❌ localhost:$PORT unavailable"
  [[ -n "$REMOTE_URL" ]] && { health "$REMOTE_URL" && say "✅ remote healthy: $REMOTE_URL" || say "❌ remote unavailable: $REMOTE_URL"; }
  say "Largest Downloads entries:"
  du -sh "$HOME"/Downloads/* 2>/dev/null | sort -h | tail -n 8 || true
}

status() {
  say "=== ZYRA CPR STATUS ==="
  [[ -f "$STATE" ]] && cat "$STATE" || say "No runtime state yet."
  say "Free disk: $(free_mb) MB"
  if health "$(local_url)"; then say "✅ localhost:$PORT healthy"; else say "❌ localhost:$PORT not healthy"; fi
  [[ -n "$REMOTE_URL" ]] && { health "$REMOTE_URL" && say "✅ remote healthy: $REMOTE_URL" || say "❌ remote unavailable: $REMOTE_URL"; }
}

stop() {
  [[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" >/dev/null 2>&1 || true
  rm -f "$PIDFILE" 2>/dev/null || true
  pkill -f "llama-server.*--port ${PORT}" >/dev/null 2>&1 || true
  say "🛑 ZYRA worker stopped"
}

case "${1:-heal}" in
  heal) heal ;;
  start) start_local ;;
  clean) safe_cleanup; say "✅ CPR cache cleanup complete. Free disk: $(free_mb) MB" ;;
  doctor) doctor ;;
  status) status ;;
  stop) stop ;;
  *) say "Usage: $0 {heal|start|clean|doctor|status|stop}"; exit 2 ;;
esac
