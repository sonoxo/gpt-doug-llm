#!/usr/bin/env bash
set -euo pipefail

# GPT-DOUG-LLM bridge -> Sonoxomus Agentic CPR / Red Panda integration.
# This keeps Sonoxomus as the canonical implementation while making the
# command below work from the gpt-doug-llm checkout:
#   bash integrations/agentic-cpr-red-panda/activate.sh --install

SONOXOMUS_DIR="${SONOXOMUS_DIR:-${HOME}/.local/share/Sonoxomus}"
SONOXOMUS_REPO="https://github.com/sonoxo/Sonoxomus.git"
SONOXOMUS_BRANCH="master"
TARGET_REL="integrations/agentic-cpr-red-panda/activate.sh"
TARGET="${SONOXOMUS_DIR}/${TARGET_REL}"

log() { printf '🐼 %s\n' "$*"; }
fail() { printf '❌ %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || fail "git is required."

if [[ ! -d "${SONOXOMUS_DIR}/.git" ]]; then
  log "Sonoxomus not found locally; cloning canonical runtime…"
  mkdir -p "$(dirname "${SONOXOMUS_DIR}")"
  git clone --depth 1 --branch "${SONOXOMUS_BRANCH}" "${SONOXOMUS_REPO}" "${SONOXOMUS_DIR}"
else
  log "Refreshing Sonoxomus ${SONOXOMUS_BRANCH}…"
  git -C "${SONOXOMUS_DIR}" fetch origin "${SONOXOMUS_BRANCH}"
  git -C "${SONOXOMUS_DIR}" checkout "${SONOXOMUS_BRANCH}"
  git -C "${SONOXOMUS_DIR}" pull --ff-only origin "${SONOXOMUS_BRANCH}"
fi

[[ -f "${TARGET}" ]] || fail "Canonical Red Panda activator missing at ${TARGET}"

log "Delegating Agentic CPR to Sonoxomus…"
exec bash "${TARGET}" "$@"
