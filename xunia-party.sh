#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MODE="${1:-party}"

if command -v say >/dev/null 2>&1; then
  say "GPT XUNIA SUPER BRAIN 9000 ONLINE" >/dev/null 2>&1 &
fi

python3 - <<'PY'
import os
import random
import sys
import time

colors = ["\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[94m", "\033[95m"]
icons = ["*", "+", "x", "o", "@", "#", "~"]
logo = r"""
        ██████╗ ██████╗ ████████╗    ██╗  ██╗██╗   ██╗███╗   ██╗██╗ █████╗
        ██╔════╝ ██╔══██╗╚══██╔══╝    ╚██╗██╔╝██║   ██║████╗  ██║██║██╔══██╗
        ██║  ███╗██████╔╝   ██║        ╚███╔╝ ██║   ██║██╔██╗ ██║██║███████║
        ██║   ██║██╔═══╝    ██║        ██╔██╗ ██║   ██║██║╚██╗██║██║██╔══██║
        ╚██████╔╝██║        ██║       ██╔╝ ██╗╚██████╔╝██║ ╚████║██║██║  ██║
         ╚═════╝ ╚═╝        ╚═╝       ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝

                  SUPER XUNIA BRAIN 9000
          OPENAI + CLAUDE + GEMINI + OLLAMA
                   >>> GPT DOUG XO <<<
"""

sys.stdout.write("\033[?25l")
sys.stdout.flush()
try:
    for frame in range(36):
        os.system("clear")
        for _ in range(7):
            row = []
            for _ in range(76):
                if random.random() < 0.075:
                    row.append(random.choice(colors) + random.choice(icons) + "\033[0m")
                else:
                    row.append(" ")
            print("".join(row))
        print(random.choice(colors) + logo + "\033[0m")
        print("\033[1;96m              LIVE STREAMING LAYERS READY\033[0m")
        time.sleep(0.09)
finally:
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

print("\n\033[1;96mGPT XUNIA PARTY MODE: ONLINE\033[0m")
PY

if [[ "$MODE" == "run" ]]; then
  export GPT_DOUG_PROVIDER="${GPT_DOUG_PROVIDER:-xunia}"
  export GPT_DOUG_PROVIDER_ORDER="${GPT_DOUG_PROVIDER_ORDER:-claude,openai,gemini,ollama}"
  chmod +x web/doug-web.sh
  ./web/doug-web.sh restart

  if command -v open >/dev/null 2>&1; then
    open "http://localhost:${PORT:-8787}"
  fi

  echo
  echo "GPT XUNIA runtime: http://localhost:${PORT:-8787}"
fi
