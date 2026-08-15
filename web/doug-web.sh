#!/usr/bin/env bash
# Process supervisor for the GPT Doug web server: start/stop/restart/status
# with a pidfile, so you don't need to hand-manage `nohup`/`kill` anymore.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="$DIR/.server.pid"
LOGFILE="$DIR/server.log"
PORT="${PORT:-8787}"

is_running() {
  [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

start() {
  if is_running; then
    echo "already running (pid $(cat "$PIDFILE"), port $PORT)"
    return 0
  fi
  # Clean up anything else squatting on the port from outside this supervisor.
  local stray
  stray=$(lsof -ti ":$PORT" 2>/dev/null || true)
  if [[ -n "$stray" ]]; then
    echo "killing stray process(es) on port $PORT: $stray"
    kill -9 $stray 2>/dev/null || true
    sleep 0.5
  fi
  cd "$DIR"
  nohup python3 server.py > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  disown
  sleep 1
  if is_running; then
    echo "started (pid $(cat "$PIDFILE")) — http://localhost:$PORT"
  else
    echo "failed to start — check $LOGFILE"
    tail -20 "$LOGFILE" || true
    exit 1
  fi
}

stop() {
  if ! is_running; then
    echo "not running"
    rm -f "$PIDFILE"
    return 0
  fi
  local pid
  pid=$(cat "$PIDFILE")
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.3
  done
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PIDFILE"
  echo "stopped"
}

status() {
  if is_running; then
    echo "running (pid $(cat "$PIDFILE"), port $PORT)"
  else
    echo "stopped"
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  *) echo "usage: $0 {start|stop|restart|status}"; exit 1 ;;
esac
