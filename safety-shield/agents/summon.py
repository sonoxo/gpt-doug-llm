#!/usr/bin/env python3
import json
from pathlib import Path

manifest = json.loads((Path(__file__).parent / "fleet-24.json").read_text())
print(f"SUMMONING {len(manifest['agents'])} SAFETY-SHIELD AGENTS")
for a in manifest["agents"]:
    print(f"[{a['id']:02d}] {a['name']}: {a['mission']}")
print("\nFleet declared. Execution remains policy-gated and least-privileged.")
