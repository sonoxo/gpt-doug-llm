#!/bin/sh
# Zero-cost startup: optional Python CoT 2.0 gateway (default), static site, Docker.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PORT="${TAK_OS_PORT:-8080}"
case "$PORT" in ''|*[!0-9]*) echo 'TAK_OS_PORT must be numeric' >&2; exit 2 ;; esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then echo 'Port must be between 1024 and 65535' >&2; exit 2; fi
case "${1:-web}" in
  web|gateway)
    command -v python3 >/dev/null || { echo 'Install free Python 3'; exit 1; }
    printf 'GPT-DOUG TAK-OS / CoT 2.0 lab: http://127.0.0.1:%s\n' "$PORT"
    exec python3 -u gateway.py --bind 127.0.0.1 --port "$PORT";;
  legacy-udp)
    command -v python3 >/dev/null || { echo 'Install free Python 3'; exit 1; }
    printf 'GPT-DOUG TAK-OS / CoT UDP loopback on 6969. Lab only.\n'
    exec python3 -u gateway.py --bind 127.0.0.1 --port "$PORT" --udp-port 6969;;
  legacy-tcp)
    command -v python3 >/dev/null || { echo 'Install free Python 3'; exit 1; }
    printf 'GPT-DOUG TAK-OS / CoT TCP loopback on 8087. Lab only.\n'
    exec python3 -u gateway.py --bind 127.0.0.1 --port "$PORT" --tcp-port 8087;;
  static)
    command -v python3 >/dev/null || { echo 'Install Python 3'; exit 1; }
    printf 'GPT-DOUG TAK-OS / browser-only fallback: http://127.0.0.1:%s\n' "$PORT"
    exec python3 -m http.server "$PORT" --bind 127.0.0.1;;
  docker)
    command -v docker >/dev/null || { echo 'Install Docker Engine/Compose'; exit 1; }
    exec docker compose up --build -d --wait;;
  test)
    exec python3 -m unittest discover -s ../../tests -p 'test_tak_os_gateway.py' -v;;
  *) echo 'Usage: sh start.sh [web|static|legacy-udp|legacy-tcp|docker|test]' >&2; exit 2;;
esac
