#!/usr/bin/env bash
# Explicit opt-in: free real pretrained Wan2.2 model via MLX-Gen on capable Macs.
# Model weighs ~17 GiB and needs significant unified memory at runtime.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ "$(uname -s)" != 'Darwin' || "$(uname -m)" != 'arm64' ]]; then
  echo 'This optional installer is for Apple Silicon. NVIDIA users can use official ComfyUI/Wan or free-video-studio.' >&2
  exit 2
fi
MEM_BYTES="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
MEM_GIB=$(( MEM_BYTES / 1024 / 1024 / 1024 ))
DISK_KIB="$(df -Pk "$HOME" | awk 'NR==2 {print $4}')"
DISK_GIB=$(( DISK_KIB / 1024 / 1024 ))
echo "Unified memory: ${MEM_GIB} GiB; available disk space: ${DISK_GIB} GiB"
if (( DISK_GIB < 30 )); then
  echo 'At least 30 GiB free is required to download and install model weights. Nothing was downloaded.' >&2
  exit 2
fi
if (( MEM_GIB < 48 )) && [[ "${CINEMA_ALLOW_LOW_MEMORY:-0}" != 1 ]]; then
  echo 'Wan2.2 5B may exceed this Mac memory. Recommended 48+ GiB for attempting low-resolution renders.' >&2
  echo 'Explicitly override with CINEMA_ALLOW_LOW_MEMORY=1 if you accept crashes/swapping; this does not guarantee success.' >&2
  exit 2
fi
if command -v python3.12 >/dev/null 2>&1; then PY="$(command -v python3.12)";
elif command -v python3.11 >/dev/null 2>&1; then PY="$(command -v python3.11)";
else
  echo 'Python 3.11/3.12 required for the optional MLX engine. Free: brew install python@3.12' >&2; exit 2
fi
"$PY" -m venv "$ROOT/cinema_studio/.venv"
VENV="$ROOT/cinema_studio/.venv/bin"
"$VENV/python" -m pip install --upgrade pip
"$VENV/python" -m pip install --upgrade mlx-gen
MODEL='AbstractFramework/wan2.2-ti2v-5b-diffusers-8bit'
echo "Downloading open model $MODEL (~17 GiB). No paid API or model subscription."
"$VENV/mlxgen" download --model "$MODEL"
echo 'Done. Return to the local Studio at http://127.0.0.1:8793/ and refresh engine status.'
