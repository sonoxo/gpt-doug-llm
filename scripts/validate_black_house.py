#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from black_house_kernel import validate_kernel

ROOT = Path(__file__).resolve().parents[1]
BH = ROOT / "the-black-house"

REQUIRED_FILES = [
    BH / "README.md",
    BH / "ecosystem.yaml",
    BH / "registry" / "repositories.json",
    BH / "registry" / "services.json",
    BH / "registry" / "agents.json",
    BH / "missions" / "mission.schema.json",
    BH / "missions" / "router.manifest.json",
    BH / "missions" / "history.schema.json",
    BH / "ontology" / "ontology.schema.json",
    BH / "kernel" / "kernel.manifest.json",
    BH / "kernel" / "kernel.schema.json",
    BH / "runtime" / "runtime-contract.json",
    BH / "telemetry" / "telemetry.schema.json",
    BH / "integrations" / "palantir" / "status.schema.json",
    BH / "status" / "phases.json",
    BH / "governance" / "CONTROL-PLANE.md",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"BLACK HOUSE VALIDATION FAILED: {message}")


def main() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.is_file()]
    require(not missing, f"missing required files: {', '.join(missing)}")

    ecosystem = (BH / "ecosystem.yaml").read_text(encoding="utf-8")
    require(
        "controlPlane: THE_BLACK_HOUSE_V1" in ecosystem,
        "ecosystem control-plane identity mismatch",
    )
    require("missionProtocol: black-house-mission-v1" in ecosystem, "mission protocol missing")

    repositories = load_json(BH / "registry" / "repositories.json")
    repo_ids = {item["id"] for item in repositories["repositories"]}
    require(
        {"GPT_DOUG_LLM", "ZYRA", "XUNIA", "AIP_REGISTRY"}.issubset(repo_ids),
        "core repository registry is incomplete",
    )

    services = load_json(BH / "registry" / "services.json")
    service_ids = {item["id"] for item in services["services"]}
    require(
        {
            "RVIA_ROUTER",
            "SHADOW_GLASS",
            "GLASS_ONION",
            "ZYRA_CORE",
            "ZYRA_CLOUD",
            "XUNIA_CORE",
            "NXYZ",
        }.issubset(service_ids),
        "core service registry is incomplete",
    )

    agents = load_json(BH / "registry" / "agents.json")
    agent_ids = {item["id"] for item in agents["agents"]}
    require(
        {"GPT_DOUG_MAX", "VIRGINIA", "VA3LM", "WAKEUP3LM"}.issubset(agent_ids),
        "agent registry is incomplete",
    )

    mission = load_json(BH / "missions" / "mission.schema.json")
    mission_required = set(mission["required"])
    require(
        {
            "missionId",
            "requestedBy",
            "intent",
            "target",
            "classification",
            "approvalState",
            "evidence",
            "audit",
        }.issubset(mission_required),
        "mission envelope required fields are incomplete",
    )
    mission_properties = set(mission["properties"])
    require(
        {"mutation", "metadata", "requiredCapabilities", "allowedTools"}.issubset(
            mission_properties
        ),
        "mission routing fields are incomplete",
    )

    router = load_json(BH / "missions" / "router.manifest.json")
    require(router["protocol"] == "black-house-mission-v1", "RVIA mission protocol mismatch")
    require(router["failClosed"] is True, "RVIA router must fail closed")
    require(
        {
            "RVIA",
            "IDENTITY",
            "SHADOW_GLASS",
            "ONTOLOGY_CONTEXT",
            "PLANNER",
            "ZYRA_AUTHORIZATION",
            "DISPATCH",
            "GLASS_ONION",
            "EVIDENCE",
            "AUDIT",
        }.issubset(set(router["stages"])),
        "RVIA routing stages are incomplete",
    )
    require(
        {
            "GPT_DOUG_MAX",
            "VIRGINIA",
            "WAKEUP3LM",
            "ZYRA",
            "XUNIA",
            "NXYZ",
            "ZYRA_CLOUD",
            "AIP_REGISTRY",
            "PALANTIR",
        }.issubset(set(router["targets"])),
        "RVIA target registry is incomplete",
    )

    kernel = validate_kernel()
    require(kernel["kernelVersion"] == "3.0.0", "phase 3 kernel version mismatch")
    binding_ids = {item["component"] for item in kernel["bindings"]}
    require(
        {"VA3LM", "WAKEUP3LM", "XUNIA", "ZYRA", "AIP_REGISTRY"}.issubset(binding_ids),
        "kernel consumer bindings are incomplete",
    )

    ontology = load_json(BH / "ontology" / "ontology.schema.json")
    object_types = set(ontology["properties"]["objects"]["items"]["enum"])
    relationship_types = set(ontology["properties"]["relationships"]["items"]["enum"])
    require(
        set(kernel["objectTypes"]) == object_types,
        "ontology object vocabulary drifted from kernel",
    )
    require(
        set(kernel["relationshipTypes"]) == relationship_types,
        "ontology relationship vocabulary drifted from kernel",
    )
    require(
        {"Mission", "Agent", "Repository", "Service", "Evidence", "Policy"}.issubset(
            object_types
        ),
        "ontology object vocabulary is incomplete",
    )
    require(
        {"EXECUTES", "PRODUCES", "GOVERNS", "IMPLEMENTS", "AUDITS"}.issubset(
            relationship_types
        ),
        "ontology relationship vocabulary is incomplete",
    )

    runtime = load_json(BH / "runtime" / "runtime-contract.json")
    require(
        runtime["controlPlane"] == "THE_BLACK_HOUSE_V1",
        "runtime control-plane identity mismatch",
    )
    require(runtime["localRuntime"]["port"] == 8088, "VA3LM runtime port must remain 8088")
    require(
        runtime["localRuntime"]["healthPath"] == "/healthz",
        "VA3LM health contract mismatch",
    )

    telemetry = load_json(BH / "telemetry" / "telemetry.schema.json")
    require(
        telemetry["properties"]["provider"]["const"] == "github",
        "telemetry provider contract mismatch",
    )

    palantir = load_json(BH / "integrations" / "palantir" / "status.schema.json")
    verification_states = set(palantir["properties"]["verificationState"]["enum"])
    require(
        {"LIVE_TENANT_UNVERIFIED", "LIVE_TENANT_VERIFIED"}.issubset(verification_states),
        "Palantir verification truth states are incomplete",
    )

    phase_status = load_json(BH / "status" / "phases.json")
    phases = {item["phase"]: item for item in phase_status["phases"]}
    require(set(phases) == set(range(1, 9)), "phase status must cover phases 1 through 8")
    require(
        all(phases[number]["codeState"] == "COMPLETE" for number in range(1, 9)),
        "all phase implementations must be code-complete",
    )
    require(
        phases[7].get("externalState") in {"LIVE_TENANT_UNVERIFIED", "LIVE_TENANT_VERIFIED"},
        "phase 7 must expose an explicit tenant verification state",
    )

    print("BLACK HOUSE CONTROL PLANE: GREEN")
    print(
        f"kernel=3.0.0 repositories={len(repo_ids)} services={len(service_ids)} "
        f"agents={len(agent_ids)}"
    )
    print(
        f"ontology_objects={len(object_types)} "
        f"ontology_relationships={len(relationship_types)}"
    )
    print("runtime_contract=BLACK_HOUSE_RUNTIME_V1 port=8088")
    print("phases=1-8 code_complete phase7_external_state=" + phases[7]["externalState"])


if __name__ == "__main__":
    main()
