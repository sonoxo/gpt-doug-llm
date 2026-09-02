#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).parent
manifest = json.loads((ROOT / "fleet-24.json").read_text())
knowledge_path = ROOT / manifest["operating_model"]["knowledge_path"]
knowledge = json.loads(knowledge_path.read_text())
expected_profile = manifest["operating_model"]["knowledge_profile"]

if knowledge.get("profile") != expected_profile:
    raise SystemExit(
        f"Knowledge profile mismatch: fleet={expected_profile} knowledge={knowledge.get('profile')}"
    )

mismatched = [
    agent["name"]
    for agent in manifest["agents"]
    if agent.get("knowledge_profile") != expected_profile
]
if mismatched:
    raise SystemExit("Agents missing current knowledge profile: " + ", ".join(mismatched))

print(f"SUMMONING {len(manifest['agents'])} SAFETY-SHIELD AGENTS")
print(f"KNOWLEDGE PROFILE: {expected_profile} v{knowledge['version']}")
print("AGENTIC LOOP: " + " -> ".join(knowledge["agentic_loop"]))
print()

for agent in manifest["agents"]:
    print(
        f"[{agent['id']:02d}] {agent['name']}: {agent['mission']} "
        f"[knowledge={agent['knowledge_profile']}]"
    )

print("\nFleet knowledge verified. Execution remains policy-gated and least-privileged.")
