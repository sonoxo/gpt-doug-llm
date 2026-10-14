#!/bin/sh
set -eu

python3 -m py_compile src/core.py src/service.py
python3 -m unittest discover -s tests -v

if command -v docker >/dev/null 2>&1; then
  docker build -t gpt-doug-qbio:validation .
fi
