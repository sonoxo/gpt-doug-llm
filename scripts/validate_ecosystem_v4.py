#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "ecosystem" / "registry.v4.json"
AI_MANIFEST = ROOT / "config" / "ai-layer-manifest.json"

EXPECTED_PLANES = {
    "black-house",
    "xunia-hq",
    "xunia-domain-root",
    "zyra",
    "red-house",
    "green-house",
    "orange-house",
    "glass-onion-spatial",
}
EXPECTED_AI_LAYERS = {
    "classical_ai",
    "machine_learning",
    "neural_networks",
    "deep_learning",
    "generative_ai",
    "agentic_ai",
}


def fail(message: str) -> None:
    raise SystemExit(f"ecosystem-v4 validation failed: {message}")


def main() -> None:
    if not REGISTRY.exists():
        fail("missing ecosystem/registry.v4.json")
    if not AI_MANIFEST.exists():
        fail("missing config/ai-layer-manifest.json")

    registry = json.loads(REGISTRY.read_text())
    ai = json.loads(AI_MANIFEST.read_text())

    if registry.get("ecosystem_version") != "4.0.0":
        fail("ecosystem_version must be 4.0.0")
    if registry.get("canonical_control_root") != "sonoxo/gpt-doug-llm":
        fail("canonical control root drifted")
    if registry.get("canonical_hub") != "sonoxo/xuniahub":
        fail("canonical hub drifted")
    if registry.get("domain_registry") != "sonoxo/xuniadao":
        fail("XUNIAverse domain registry drifted")
    if registry.get("execution_plane") != "sonoxo/zyra":
        fail("execution plane drifted")

    planes = registry.get("core_planes", [])
    plane_ids = {p.get("id") for p in planes}
    if plane_ids != EXPECTED_PLANES:
        fail(f"core plane mismatch: {sorted(plane_ids)}")

    repos = [p.get("repo") for p in planes]
    if len(repos) != len(set(repos)):
        fail("duplicate core repository")
    if any(not str(repo).startswith("sonoxo/") for repo in repos):
        fail("every core repository must be an explicit sonoxo repo")
    if any(not p.get("responsibilities") for p in planes):
        fail("every core plane needs responsibilities")

    required_layers = set(ai.get("required_layer_ids", []))
    declared_layers = {layer.get("id") for layer in ai.get("layers", [])}
    if required_layers != EXPECTED_AI_LAYERS or declared_layers != EXPECTED_AI_LAYERS:
        fail("six-layer AI contract is incomplete")

    rules = " ".join(registry.get("architecture_rules", [])).lower()
    for phrase in ("human-governed", "upstream", "authorization", "does not supersede"):
        if phrase not in rules:
            fail(f"missing architecture boundary containing: {phrase}")

    routing = registry.get("domain_routing", {})
    known = EXPECTED_PLANES
    for domain, target in routing.items():
        if target not in known:
            fail(f"domain route {domain!r} points to unknown plane {target!r}")

    flow = registry.get("canonical_flow", [])
    for required in ("xunia-hq", "black-house", "xunia-domain-root", "zyra", "evidence", "human-review"):
        if required not in flow:
            fail(f"canonical flow missing {required}")

    print("ecosystem-v4: PASS")
    print(f"core planes: {len(planes)}")
    print(f"AI layers: {len(declared_layers)}/6")
    print(f"research satellites: {len(registry.get('research_satellites', []))}")


if __name__ == "__main__":
    main()
