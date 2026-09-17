#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m pip install --user pyautogui >/dev/null 2>&1 || true
python3 server.py
