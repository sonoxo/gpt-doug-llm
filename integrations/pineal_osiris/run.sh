#!/bin/sh
set -eu
# Pinned official OSIRIS local launcher; MIT upstream license retained.
case "$1" in
  url) echo 'http://127.0.0.1:3000/?layers=maritime,satellites,cctv,cctv_previews,live_news,earthquakes,global_incidents,day_night,cables,sdk_air,sdk_naval'; exit 0 ;;
  doctor) git --version && node --version && npm --version; exit 0 ;;
  sync)
    ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
    python3 "$ROOT/integrations/osiris_mirror/osiris_mirror.py" --once --base-url http://127.0.0.1:3000
    python3 "$ROOT/integrations/pineal_osiris/bridge.py"
    exit ;;
  run|'') ;;
  *) echo 'usage: sh run.sh [doctor|url|run|sync]' >&2; exit 2 ;;
esac
for cmd in git node npm; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 2; }; done
node -e 'if (Number(process.versions.node.split(".")[0]) < 20) process.exit(1)' || { echo 'Node >=20 required' >&2; exit 2; }
URL=https://github.com/simplifaisoul/osiris.git
PIN=0aaba3838b550f83eeeaea99e5179d24f85ad65c
DEST="$HOME/.local/share/gpt-doug/osiris-ui"
if [ -e "$DEST" ] && [ ! -d "$DEST/.git" ]; then echo 'Destination exists and is not a checkout' >&2; exit 2; fi
if [ ! -d "$DEST/.git" ]; then mkdir -p "$(dirname -- "$DEST")"; git clone --filter=blob:none "$URL" "$DEST"; fi
if [ "$(git -C "$DEST" remote get-url origin)" != "$URL" ]; then echo 'Unexpected upstream origin' >&2; exit 2; fi
if [ -n "$(git -C "$DEST" status --porcelain)" ]; then echo 'Upstream worktree modified' >&2; exit 2; fi
git -C "$DEST" fetch --depth=1 origin "$PIN"
git -C "$DEST" checkout --detach "$PIN"
grep -q 'MIT License' "$DEST/LICENSE" || { echo 'Missing MIT license' >&2; exit 2; }
cd "$DEST"
npm ci --no-audit --no-fund
echo 'Open selected layers:'
sh "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/run.sh" url
NEXT_TELEMETRY_DISABLED=1 npm run dev -- --hostname 127.0.0.1 --port 3000
