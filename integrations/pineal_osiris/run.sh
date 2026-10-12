#!/bin/sh
# GPT-Doug PINEAL x OSIRIS: pinned, loopback-only local dashboard.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SELF="$ROOT/integrations/pineal_osiris"
UPSTREAM='https://github.com/simplifaisoul/osiris.git'
PIN=${OSIRIS_REF:-0aaba3838b550f83eeeaea99e5179d24f85ad65c}
WORKTREE=${OSIRIS_WORKTREE:-"$HOME/.local/share/gpt-doug/osiris-ui"}
PORT=${OSIRIS_PORT:-3000}
LAYERS='maritime,satellites,cctv,cctv_previews,live_news,earthquakes,global_incidents,day_night,cables,sdk_air,sdk_naval'
case "$PORT" in ''|*[!0-9]*) echo 'OSIRIS_PORT must be numeric' >&2; exit 2;; esac
if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then echo 'OSIRIS_PORT must be 1024..65535' >&2; exit 2; fi
BASE="http://127.0.0.1:$PORT"
URL="$BASE/?layers=$LAYERS"
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 2; }; }
check_prereqs() {
  need git; need node; need npm; need python3
  node -e 'const v=process.versions.node.split(".").map(Number); process.exit(v[0]>20||(v[0]===20&&v[1]>=9)?0:1)' || {
    echo 'OSIRIS Next.js requires Node.js 20.9+ (Node 22 LTS recommended)' >&2; exit 2;
  }
  python3 -c 'import sys; assert sys.version_info >= (3, 10)' || {
    echo 'PINEAL bridge requires Python 3.10+' >&2; exit 2;
  }
}
check_ref() {
  if [ "${#PIN}" -ne 40 ]; then echo 'OSIRIS_REF must be 40 lowercase hex digits' >&2; exit 2; fi
  case "$PIN" in *[!0123456789abcdef]*) echo 'OSIRIS_REF must be 40 lowercase hex digits' >&2; exit 2;; esac
}
prepare_upstream() {
  need git; need node; need npm
  check_ref
  if [ -e "$WORKTREE" ] && [ ! -d "$WORKTREE/.git" ]; then
    echo "Refusing unexpected existing OSIRIS directory: $WORKTREE" >&2; exit 2
  fi
  if [ ! -d "$WORKTREE/.git" ]; then
    mkdir -p "$(dirname -- "$WORKTREE")"
    git clone --filter=blob:none "$UPSTREAM" "$WORKTREE"
  fi
  origin=$(git -C "$WORKTREE" remote get-url origin)
  if [ "$origin" != "$UPSTREAM" ]; then
    echo "Refusing OSIRIS checkout from unexpected origin: $origin" >&2; exit 2
  fi
  if [ -n "$(git -C "$WORKTREE" status --porcelain)" ]; then
    echo 'Refusing modified OSIRIS source worktree; review it manually' >&2; exit 2
  fi
  git -C "$WORKTREE" fetch --depth=1 origin "$PIN"
  git -C "$WORKTREE" checkout --detach "$PIN"
  grep -q 'MIT License' "$WORKTREE/LICENSE" || { echo 'Expected MIT LICENSE missing' >&2; exit 2; }
  # A completed installer marker, written only AFTER npm ci succeeds, prevents
  # a failed ENOSPC extraction from ever being mistaken for an installed app.
  marker="$WORKTREE/node_modules/.gpt-doug-osiris-install-ok"
  if [ ! -f "$marker" ] || [ "$WORKTREE/package-lock.json" -nt "$marker" ]; then
    python3 "$SELF/disk.py" preflight --worktree "$WORKTREE" --minimum-mb "${OSIRIS_MIN_FREE_MB:-4096}" || exit 2
    if (cd "$WORKTREE" && npm ci --no-audit --no-fund); then
      printf '%s\n' "$PIN" > "$marker"
    else
      echo 'OSIRIS dependency install failed. If npm reported ENOSPC, do not rerun without reclaiming space.' >&2
      echo "Try: sh '$SELF/run.sh' repair-cache" >&2
      echo 'Then verify: df -h "$HOME"' >&2
      exit 2
    fi
  fi
}
run_sync() {
  need python3
  if python3 "$ROOT/integrations/osiris_mirror/osiris_mirror.py" --once --base-url "$BASE"; then
    :
  else
    exitcode=$?
    if [ "$exitcode" -ne 2 ]; then exit "$exitcode"; fi
    echo 'Public OSIRIS routes currently offline; recording degraded statuses.' >&2
  fi
  python3 "$SELF/bridge.py"
}
case "${1:-stack}" in
  console) printf 'http://127.0.0.1:%s/\n' "${PINEAL_OSIRIS_CONSOLE_PORT:-8766}" ;;
  help|-h|--help)
    echo 'Usage: sh run.sh [stack|run|sync|status|doctor|url|console|disk|repair|repair-cache]'
    echo 'stack installs OSIRIS, launches map and keeps PINEAL public-feed health synchronized'
    echo 'run starts OSIRIS only; sync captures approved health once; status checks local state'
    echo 'disk shows free space; repair removes only managed node_modules; repair-cache also clears shared npm download cache'
    ;;
  url) printf '%s\n' "$URL" ;;
  doctor)
    check_prereqs
    python3 "$SELF/disk.py" status --worktree "$WORKTREE"
    printf 'Prerequisites: OK. OSIRIS source pinned at %s\nMap: %s\nConsole: http://127.0.0.1:%s/\n' "$PIN" "$URL" "${PINEAL_OSIRIS_CONSOLE_PORT:-8766}"
    ;;
  disk)
    need python3
    python3 "$SELF/disk.py" status --worktree "$WORKTREE"
    ;;
  repair|repair-cache)
    need python3
    python3 "$SELF/disk.py" "$1" --worktree "$WORKTREE" --port "$PORT"
    ;;
  sync) run_sync ;;
  status)
    need python3
    python3 "$SELF/stack.py" status --port "$PORT"
    ;;
  run)
    prepare_upstream
    printf '\nOSIRIS map URL: %s\n' "$URL"
    cd "$WORKTREE"
    NEXT_TELEMETRY_DISABLED=1 npm run dev -- --hostname 127.0.0.1 --port "$PORT"
    ;;
  stack)
    check_prereqs
    exec python3 "$SELF/stack.py" start --port "$PORT" --interval "${OSIRIS_SYNC_INTERVAL:-300}" --launcher "$SELF/run.sh" --console-port "${PINEAL_OSIRIS_CONSOLE_PORT:-8766}"
    ;;
  *) echo 'Usage: sh run.sh [stack|run|sync|status|doctor|url|console|disk|repair|repair-cache]' >&2; exit 2 ;;
esac
