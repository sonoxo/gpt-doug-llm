#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

command -v python3 >/dev/null || { echo "❌ python3 is required"; exit 1; }
command -v git >/dev/null || { echo "❌ git is required"; exit 1; }

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
mkdir -p vendor models outputs

if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "🍎 Apple Silicon path: MLX-Gen + Wan2.2 TI2V-5B"
  python -m pip install -U mlx-gen
  mlxgen download --model AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit
  echo "✅ Apple Silicon backend installed. No paid inference API is configured."
else
  echo "🟢 CUDA path: official Wan2.2 TI2V-5B"
  if [[ ! -d vendor/Wan2.2/.git ]]; then
    git clone --depth 1 https://github.com/Wan-Video/Wan2.2.git vendor/Wan2.2
  fi
  python -m pip install -r vendor/Wan2.2/requirements.txt
  python -m pip install "huggingface_hub[cli]"

  if [[ ! -d models/Wan2.2-TI2V-5B || -z "$(ls -A models/Wan2.2-TI2V-5B 2>/dev/null || true)" ]]; then
    mkdir -p models/Wan2.2-TI2V-5B
    if command -v hf >/dev/null 2>&1; then
      hf download Wan-AI/Wan2.2-TI2V-5B --local-dir models/Wan2.2-TI2V-5B
    else
      huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir models/Wan2.2-TI2V-5B
    fi
  fi

  if [[ "${INSTALL_MMAUDIO:-0}" == "1" ]]; then
    if [[ ! -d vendor/MMAudio/.git ]]; then
      git clone --depth 1 https://github.com/hkchengrex/MMAudio.git vendor/MMAudio
    fi
    python -m pip install -e vendor/MMAudio
    echo "🔊 MMAudio installed. Its pretrained weights download automatically on first audio generation."
  fi
fi

echo "✅ FREE VIDEO STUDIO installed"
echo "Run: bash run.sh"
