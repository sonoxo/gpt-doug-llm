#!/bin/sh
# Serves only public source-backed 3D UI files; DOES NOT start demo or CoT gateway.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
command -v python3 >/dev/null || { echo 'Install free Python 3 to host this static app' >&2; exit 1; }
PORT="$(python3 - <<'PY'
import socket
for port in range(8080, 8130):
    with socket.socket() as sock:
        try: sock.bind(('127.0.0.1',port))
        except OSError: continue
        print(port)
        break
else: raise SystemExit('No free loopback TCP port 8080..8129')
PY
)"
printf 'GPT-DOUG REAL EARTH 3D / NO SYNTHETIC DATA\nOpen http://127.0.0.1:%s/ in your browser.\n' "$PORT"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
