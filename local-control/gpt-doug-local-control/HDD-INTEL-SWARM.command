#!/bin/bash
set -e
cd "$(dirname "$0")"
./start.command >/tmp/gpt-doug-hdd-start.log 2>&1 &
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8765/status >/dev/null 2>&1; then break; fi
  sleep 1
done
if ! curl -fsS http://127.0.0.1:8765/status >/dev/null 2>&1; then
  echo "GPT-Doug bridge did not come online. Run diagnose.command."
  exit 1
fi
echo "GPT-Doug HDD Intel Swarm bridge ONLINE"
echo "Starting read-only metadata index of your home folder (max 25,000 files, 8 workers)..."
./ctl.py exec '{"type":"hdd_index","path":"~","workers":8,"max_files":25000}'
open http://127.0.0.1:8765
