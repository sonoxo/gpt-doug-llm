#!/usr/bin/env bash
set -euo pipefail

ROOT="${GPT_DOUG_SONOXOMUS_HOME:-$HOME/.gpt-doug/research/sonoxomus}"
REPO="$ROOT/repo"
VENV="$ROOT/.venv"
RESULTS="$ROOT/results"

mkdir -p "$ROOT" "$RESULTS"

echo "🧪 GPT-DOUG // SONOXOMUS RESEARCH SANDBOX"
echo "📁 $ROOT"
echo "💸 Paid APIs: OFF"
echo "🌐 Service binding: none"

if [[ ! -d "$REPO/.git" ]]; then
  git clone --depth 1 https://github.com/sonoxo/Sonoxomus.git "$REPO"
else
  git -C "$REPO" pull --ff-only
fi

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null

# Install the external AGPL project inside its own venv. No source is copied
# into GPT-DOUG-LLM and no model-modification command is run automatically.
if [[ -f "$REPO/pyproject.toml" ]]; then
  "$VENV/bin/pip" install -e "$REPO"
else
  "$VENV/bin/pip" install -U heretic-llm
fi

cat > "$ROOT/README.txt" <<'EOF'
GPT-DOUG Sonoxomus Research Sandbox

Purpose:
- local model evaluation
- refusal-rate / KL-divergence benchmarking
- residual-geometry / interpretability research
- comparison of local model variants

This bootstrap does not automatically remove model safety alignment and does
not grant the research dependency control over host security policy.

Useful first commands:
  source .venv/bin/activate
  heretic --help

Keep generated research outputs under ./results.
EOF

printf '✅ Ready\n'
printf 'Activate: source "%s/bin/activate"\n' "$VENV"
printf 'Repo:     %s\n' "$REPO"
printf 'Results:  %s\n' "$RESULTS"
