#!/bin/sh
# Local Mac launcher for free CoT 2.0 gateway + live browser dashboard.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
command -v python3 >/dev/null || { echo 'Python 3 required (free)'; exit 1; }
(
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health', timeout=1)" >/dev/null 2>&1; then
      open 'http://127.0.0.1:8080/'
      exit 0
    fi
    sleep 1
  done
) &
exec sh ./start.sh web
