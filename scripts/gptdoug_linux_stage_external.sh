#!/usr/bin/env bash
set -euo pipefail

# GPT-Doug Linux image staging guard.
# Copies a Linux image to a mounted external drive without repartitioning it.

IMAGE=''
DEST=''
EXPECTED=''

while [ "$#" -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --dest) DEST="$2"; shift 2 ;;
    --sha256) EXPECTED="$2"; shift 2 ;;
    -h|--help)
      echo 'Usage: gptdoug_linux_stage_external.sh --image /path/linux.iso --dest /Volumes/EXT_TB [--sha256 HASH]'
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ -n "$IMAGE" ] || { echo 'ERROR: --image is required.' >&2; exit 2; }
[ -f "$IMAGE" ] || { echo "ERROR: image not found: $IMAGE" >&2; exit 2; }
[ -n "$DEST" ] || { echo 'ERROR: --dest is required.' >&2; exit 2; }
[ -d "$DEST" ] || { echo "ERROR: destination is not mounted: $DEST" >&2; exit 2; }

hash_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    echo 'ERROR: no SHA-256 utility available.' >&2
    exit 3
  fi
}

if [ -n "$EXPECTED" ]; then
  ACTUAL=$(hash_file "$IMAGE")
  [ "$ACTUAL" = "$EXPECTED" ] || {
    echo 'ERROR: SHA-256 mismatch.' >&2
    echo "expected: $EXPECTED" >&2
    echo "actual:   $ACTUAL" >&2
    exit 4
  }
  echo '[OK] SHA-256 verified.'
fi

OS=$(uname -s)
case "$OS" in
  Darwin)
    INFO=$(diskutil info "$DEST" 2>/dev/null || true)
    echo "$INFO" | grep -Eq 'Device Location: *External|Protocol: *USB|Protocol: *Thunderbolt' || {
      echo 'ERROR: destination does not appear to be on an external macOS disk.' >&2
      exit 5
    }
    ;;
  Linux)
    DEV=$(df -P "$DEST" | awk 'NR==2 {print $1}')
    BASE=$(lsblk -no PKNAME "$DEV" 2>/dev/null | head -n1 || true)
    if [ -n "$BASE" ]; then BASE="/dev/$BASE"; else BASE="$DEV"; fi
    RM=$(lsblk -dn -o RM "$BASE" 2>/dev/null | tr -d ' ' || true)
    TRAN=$(lsblk -dn -o TRAN "$BASE" 2>/dev/null | tr -d ' ' || true)
    if [ "$RM" != '1' ] && [ "$TRAN" != 'usb' ] && [ "$TRAN" != 'thunderbolt' ]; then
      echo 'ERROR: destination does not appear to be removable/external.' >&2
      exit 5
    fi
    ;;
  *)
    echo "ERROR: unsupported OS: $OS" >&2
    exit 6
    ;;
esac

OUT="$DEST/$(basename "$IMAGE")"
echo "[GPTDOUG] staging Linux image to external drive: $OUT"
cp -v "$IMAGE" "$OUT"
sync
echo '[OK] Linux image saved to external drive.'
echo "$OUT"
