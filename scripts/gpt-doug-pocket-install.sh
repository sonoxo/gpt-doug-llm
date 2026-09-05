#!/usr/bin/env bash
set -euo pipefail

# GPT-DOUG POCKET — non-destructive USB installer.
# Stores repo, model cache, memory, logs, temp files and workspace on the external drive.
# Compute is supplied by the host Mac; no paid API is required.

REPO_URL="https://github.com/sonoxo/gpt-doug-llm.git"
TARGET="${1:-}"

say() { printf '%s\n' "$*"; }
fail() { say "❌ $*"; exit 1; }

# A shell can remain inside a directory that was deleted/moved. That makes git fail
# with: getcwd: cannot access parent directories. Move to a guaranteed live cwd first.
cd / || exit 1

if [[ "$(uname -s)" != "Darwin" ]]; then
  fail "This first Pocket installer targets macOS."
fi

if [[ -z "$TARGET" ]]; then
  if [[ -d "/Volumes/GPT-DOUG" ]]; then
    TARGET="/Volumes/GPT-DOUG"
  else
    say "Usage: $0 /Volumes/<FLASH-DRIVE-NAME>"
    say "Example: $0 /Volumes/GPT-DOUG"
    exit 2
  fi
fi

[[ -d "$TARGET" ]] || fail "Drive path does not exist: $TARGET"
case "$TARGET" in
  /Volumes/*) ;;
  *) fail "For safety, target must be a mounted external volume under /Volumes." ;;
esac

[[ -w "$TARGET" ]] || fail "Drive is not writable: $TARGET"

POCKET="$TARGET/GPT-DOUG"
mkdir -p "$POCKET"/{repo,models,cache,memory,workspace,logs,state,bin,tmp}

# Push transient writes to the USB too. This matters when the internal SSD is full.
export TMPDIR="$POCKET/tmp"
export LLAMA_CACHE="$POCKET/models"
export HF_HOME="$POCKET/models/huggingface"
export XDG_CACHE_HOME="$POCKET/cache"
export PYTHONPYCACHEPREFIX="$POCKET/cache/pycache"

FREE_MB="$(df -Pm "$TARGET" | awk 'NR==2 {print $4+0}')"
if (( FREE_MB < 900 )); then
  fail "Flash drive needs at least ~900 MB free for the compact Pocket runtime; currently ${FREE_MB} MB."
fi

cat > "$POCKET/pocket.env" <<EOF
export GPT_DOUG_POCKET="$POCKET"
export GPT_DOUG_HOME="$POCKET/state"
export GPT_DOUG_MEMORY="$POCKET/memory"
export GPT_DOUG_WORKSPACE="$POCKET/workspace"
export GPT_DOUG_LOGS="$POCKET/logs"
export LLAMA_CACHE="$POCKET/models"
export HF_HOME="$POCKET/models/huggingface"
export XDG_CACHE_HOME="$POCKET/cache"
export PYTHONPYCACHEPREFIX="$POCKET/cache/pycache"
export TMPDIR="$POCKET/tmp"
export ZYRA_PORT="9931"
export ZYRA_MODEL="ggml-org/Qwen3-0.6B-GGUF:Q4_0"
EOF

if [[ -d "$POCKET/repo/.git" ]]; then
  say "🔄 Updating GPT-DOUG-LLM on USB..."
  git -C "$POCKET/repo" pull --ff-only || true
else
  rm -rf "$POCKET/repo"
  say "📦 Cloning GPT-DOUG-LLM to USB..."
  if ! git clone --depth 1 --filter=blob:none "$REPO_URL" "$POCKET/repo"; then
    say "⚠️ Git clone failed; retrying once from a clean USB temp directory..."
    rm -rf "$POCKET/repo"
    mkdir -p "$POCKET/repo"
    cd "$POCKET/tmp"
    git clone --depth 1 "$REPO_URL" "$POCKET/repo" || fail "Unable to clone GPT-DOUG-LLM to the flash drive."
    cd /
  fi
fi

cat > "$POCKET/gpt-doug" <<'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
POCKET="$SELF_DIR"
# shellcheck disable=SC1091
source "$POCKET/pocket.env"
cd "$POCKET/repo"
exec bash "$POCKET/repo/scripts/gpt-doug-pocket-run.sh" "$@"
LAUNCHER
chmod +x "$POCKET/gpt-doug"

cat > "$POCKET/POCKET-IDENTITY.txt" <<EOF
GPT-DOUG POCKET
Mode: local-first / USB-resident state
Cost: $0 software path
Repo: sonoxo/gpt-doug-llm
Data root: $POCKET
Model cache: $POCKET/models
Memory: $POCKET/memory
Workspace: $POCKET/workspace
Logs: $POCKET/logs
Temp: $POCKET/tmp
EOF

FREE_MB="$(df -Pm "$TARGET" | awk 'NR==2 {print $4+0}')"
say ""
say "✅ GPT-DOUG POCKET INSTALLED"
say "💾 Drive: $TARGET"
say "📁 Home:  $POCKET"
say "🧠 Free:  ${FREE_MB} MB"
say "💸 Paid API: OFF"
say ""
say "Start it with:"
say "  \"$POCKET/gpt-doug\" start"
say ""
say "Nothing was formatted or erased. The installer only manages $POCKET."
