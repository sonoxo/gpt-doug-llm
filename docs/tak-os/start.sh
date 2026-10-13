#!/bin/sh
# GPL/MIT-free dependencies: Python standard library, or optional Docker Compose.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PORT="${TAK_OS_PORT:-8080}"
case "$PORT" in
  ''|*[!0-9]*) echo "TAK_OS_PORT must be numeric" >&2; exit 2 ;;
esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  echo "TAK_OS_PORT must be between 1024 and 65535" >&2; exit 2
fi
case "${1:-web}" in
  web)
    command -v python3 >/dev/null || { echo "Install Python 3 (free)"; exit 1; }
    printf 'GPT-DOUG TAK-OS (synthetic demo) -> http://127.0.0.1:%s\n' "$PORT"
    exec python3 -m http.server "$PORT" --bind 127.0.0.1
    ;;
  docker)
    command -v docker >/dev/null || { echo "Install Docker Engine + Compose"; exit 1; }
    exec docker compose up -d --wait
    ;;
  test)
    command -v python3 >/dev/null || { echo "Install Python 3"; exit 1; }
    exec python3 -m unittest discover -s ../../tests -p 'test_tak_os_static.py' -v
    ;;
  *)
    echo "Usage: ./start.sh [web|docker|test]" >&2
    exit 2
    ;;
esac
