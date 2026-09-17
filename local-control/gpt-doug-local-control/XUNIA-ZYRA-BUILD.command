#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== GPT-DOUG MAXLLM XUNIA ZYRA BUILDER ==="

if ! curl -fsS http://127.0.0.1:8765/status >/dev/null 2>&1; then
  echo "Bridge offline -> starting local control bridge..."
  ./start.command >/tmp/gpt-doug-xunia-start.log 2>&1 &
  for _ in $(seq 1 25); do
    sleep 1
    if curl -fsS http://127.0.0.1:8765/status >/dev/null 2>&1; then break; fi
  done
fi
if ! curl -fsS http://127.0.0.1:8765/status >/dev/null 2>&1; then
  echo "ERROR: local bridge did not start. Run ./diagnose.command"
  exit 1
fi

REPO="${1:-}"
if [ -z "$REPO" ]; then
  for candidate in \
    "$HOME/GPTDougWorkspaces/gpt-doug-llm" \
    "$HOME/gpt-doug-llm" \
    "$HOME/Developer/gpt-doug-llm" \
    "$HOME/Documents/gpt-doug-llm" \
    "$HOME/Desktop/gpt-doug-llm" \
    "$HOME/Downloads/gpt-doug-llm"; do
    if [ -f "$candidate/zyra_sleeper.py" ] && [ -f "$candidate/xunia_godis.py" ]; then
      REPO="$candidate"
      break
    fi
  done
fi

if [ -z "$REPO" ]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required to prepare the workspace."
    exit 2
  fi
  REPO="$HOME/GPTDougWorkspaces/gpt-doug-llm"
  mkdir -p "$(dirname "$REPO")"
  echo "No local XUNIA/ZYRA repo found -> cloning public sonoxo/gpt-doug-llm into:"
  echo "  $REPO"
  git clone --depth 1 https://github.com/sonoxo/gpt-doug-llm.git "$REPO"
fi

REPO="$(cd "$REPO" && pwd)"
if [ ! -f "$REPO/zyra_sleeper.py" ] || [ ! -f "$REPO/zyra_agent.py" ]; then
  echo "ERROR: selected workspace is not the expected XUNIA/ZYRA repo: $REPO"
  exit 3
fi

MODEL="${GPT_DOUG_MODEL:-gpt-xunia-agent}"
if ! command -v ollama >/dev/null 2>&1; then
  echo "ERROR: Ollama is not installed. The existing XUNIA/ZYRA agent uses local Ollama models."
  exit 4
fi

if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${MODEL}"; then
  for candidate in gpt-doug qwen2.5-coder qwen2.5-coder:7b; do
    if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${candidate}"; then
      MODEL="$candidate"
      break
    fi
  done
fi

if ! ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${MODEL}"; then
  echo "ERROR: no usable local coding model is installed."
  echo "Expected gpt-xunia-agent, gpt-doug, or qwen2.5-coder."
  echo "Repo doctor: cd \"$REPO\" && python3 xunia_godis.py doctor"
  exit 5
fi

DEFAULT_GOAL="Inspect the current XUNIA and ZYRA codebase, identify the highest-value software build blocker or missing integration, implement one coherent improvement, run the repository checks available to ZYRA Agent Core, keep successful changes, and stop. Do not push, deploy, access secrets, or modify anything outside this repository."
if [ "$#" -ge 2 ]; then
  shift
  GOAL="$*"
else
  GOAL="${GPT_DOUG_GOAL:-$DEFAULT_GOAL}"
fi

if git -C "$REPO" diff --quiet && git -C "$REPO" diff --cached --quiet; then
  CURRENT="$(git -C "$REPO" branch --show-current 2>/dev/null || true)"
  if [ "$CURRENT" = "main" ] || [ "$CURRENT" = "master" ]; then
    BRANCH="gpt-doug/xunia-zyra-$(date +%Y%m%d-%H%M%S)"
    git -C "$REPO" switch -c "$BRANCH" >/dev/null
    echo "Build branch: $BRANCH"
  fi
else
  echo "Workspace already has local changes; keeping the current branch and preserving them."
fi

STATUS="$(./ctl.py status)"
if printf '%s' "$STATUS" | grep -q '"panic": true'; then
  echo "ERROR: PANIC is active. The build will not override it."
  exit 6
fi

./ctl.py arm >/dev/null
trap './ctl.py disarm >/dev/null 2>&1 || true' EXIT

ACTION=$(python3 -c 'import json,sys; print(json.dumps({"type":"xunia_zyra_mission","root":sys.argv[1],"goal":sys.argv[2],"model":sys.argv[3],"max_steps":10,"max_seconds":420,"max_model_calls":16,"evolve":False}))' "$REPO" "$GOAL" "$MODEL")

echo "Workspace: $REPO"
echo "Model: $MODEL"
echo "Authority: ARMED for this bounded build mission"
echo "Mission: $GOAL"
echo
./ctl.py exec "$ACTION"
echo
STATUS_ACTION=$(python3 -c 'import json,sys; print(json.dumps({"type":"workspace_status","root":sys.argv[1]}))' "$REPO")
./ctl.py exec "$STATUS_ACTION"
echo
echo "Mission complete. Control will disarm automatically."
open "$REPO" >/dev/null 2>&1 || true
