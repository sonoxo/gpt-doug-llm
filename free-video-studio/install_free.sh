#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "⚠️  The web UI is cross-platform, but the official Wan2.2 TI2V-5B inference path is CUDA/NVIDIA-oriented."
  echo "    For full generation, run this installer on a Linux machine with a compatible NVIDIA GPU (~24 GB VRAM)."
fi

command -v python3 >/dev/null || { echo "❌ python3 is required"; exit 1; }
command -v git >/dev/null || { echo "❌ git is required"; exit 1; }
command -v ffmpeg >/dev/null || { echo "❌ ffmpeg is required and must be on PATH"; exit 1; }

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt

mkdir -p vendor models outputs

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
  echo "🔊 MMAudio installed. Its free pretrained weights download automatically on first audio generation."
fi

echo "✅ FREE VIDEO STUDIO installed"
echo "Run: bash run.sh"
