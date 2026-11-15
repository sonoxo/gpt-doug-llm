#!/usr/bin/env bash
# GLASS ONION / KRAKEN SHIELD — local zero-billing activation.
# No bank access, billing, private-vault unlocking, or paid services.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export GPT_DOUG_FREE_ONLY=true PAID_MODE=false
export GPT_DOUG_PROVIDER=ollama GPT_DOUG_PROVIDER_ORDER=ollama
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export KRAKEN_SHIELD_ENFORCE=true GPT_DOUG_ENABLE_WORKER=false
OLLAMA_MODEL="$(printenv OLLAMA_MODEL || true)"
export OLLAMA_MODEL
if [ -z "$OLLAMA_MODEL" ]; then export OLLAMA_MODEL="qwen2.5-coder:3b"; fi

PYTHON_BIN="$ROOT/.venv/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN="$(command -v python3 || true)"; fi
if [ -z "$PYTHON_BIN" ]; then
  echo "GLASS ONION: Python 3 unavailable" >&2
  exit 2
fi

verify_policy() {
  "$PYTHON_BIN" - <<'PY'
from pathlib import Path
from kraken_shield import KrakenShield

root = Path.cwd()
required = (
    root / "apps/zyra-jukebox/index.html",
    root / "apps/zyra-jukebox/glass-onion-shield.js",
    root / "apps/zyra-jukebox/app.js",
    root / "apps/zyra-jukebox/radio.js",
    root / "apps/zyra-jukebox/controls-save.js",
)
if not all(p.is_file() for p in required):
    raise SystemExit("GLASS ONION: guarded Jukebox files missing")
html = required[0].read_text(encoding="utf-8")
if ("glass-onion-shield.js" not in html or
        html.index("glass-onion-shield.js") >= html.index('src="app.js"')):
    raise SystemExit("GLASS ONION: browser policy script is not loaded first")
if not all("GlassOnionMusicShield" in p.read_text(encoding="utf-8")
           for p in (required[2], required[3], required[4])):
    raise SystemExit("GLASS ONION: music playback policy not wired")

guard = KrakenShield()
if not guard.status()["ready"]:
    raise SystemExit("GLASS ONION: shield, emergency stop, or audit not ready")
bank = guard.check_service("bank", "unconnected", "transfer")
if bank["decision"] != "BLOCK" or bank["executed"]:
    raise SystemExit("GLASS ONION: bank write policy does not deny")
music = guard.check_service(
    "music", "soundcloud", "open_public_link",
    url="https://soundcloud.com/search?q=music"
)
if music["decision"] != "ALLOW" or music["executed"]:
    raise SystemExit("GLASS ONION: public music policy failed")
if not guard.verify_audit()["valid"]:
    raise SystemExit("GLASS ONION: audit integrity failed")
print("GLASS ONION: guard verified / music link policy active / banking denied")
print("GLASS ONION: private vault remains SEALED; no external account linked")
PY
}

check_ports_free() {
  "$PYTHON_BIN" - <<'PY'
import socket
for port in (8787, 8844):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", port))
        except OSError:
            raise SystemExit(
                f"GLASS ONION: localhost:{port} already occupied; "
                "do not overwrite or terminate an existing service"
            )
PY
}

status() {
  "$PYTHON_BIN" -m kraken_shield status || return 1
  "$PYTHON_BIN" -m kraken_shield services
  "$PYTHON_BIN" - <<'PY'
import socket
for port, name in ((8787, "CL1 UI"), (8844, "Jukebox")):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            print(f"{name}: port {port} accepts TCP (service identity not verified)")
    except OSError:
        print(f"{name}: localhost port {port} not listening")
PY
}

doctor() {
  bash scripts/cl1-free-swarm.sh doctor
  verify_policy
}

activate() {
  doctor
  check_ports_free
  "$PYTHON_BIN" -m http.server 8844 --bind 127.0.0.1 \
    --directory apps/zyra-jukebox &
  jukebox_pid=$!
  cleanup() {
    kill "$jukebox_pid" 2>/dev/null || true
    wait "$jukebox_pid" 2>/dev/null || true
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  sleep 1
  if ! kill -0 "$jukebox_pid" 2>/dev/null; then
    echo "GLASS ONION: Jukebox did not start" >&2
    return 1
  fi
  echo "GLASS ONION Jukebox: http://127.0.0.1:8844"
  echo "KRAKEN SHIELD CL1: http://127.0.0.1:8787"
  echo "Only cooperating local app paths are guarded. Leave Terminal open."
  bash scripts/cl1-free-swarm.sh run
}

case "${1:-status}" in
  activate) activate ;;
  doctor) doctor ;;
  status) status ;;
  *)
    echo "Usage: bash scripts/glass-onion-activate.sh {activate|doctor|status}" >&2
    exit 2
    ;;
esac
