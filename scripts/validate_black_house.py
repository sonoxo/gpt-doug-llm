#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BH = ROOT / "the-black-house"

REQUIRED_FILES = [
    BH / "README.md",
    BH / "ecosystem.yaml",
    BH / "registry" / "repositories.json",
    BH / "registry" / "services.json",
    BH / "registry" / "agents.json",
    BH / "missions" / "mission.schema.json",
    BH / "ontology" / "ontology.schema.json",
    BH / "runtime" / "runtime-contract.json",
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
    require("controlPlane: THE_BLACK_HOUSE_V1" in ecosystem, "ecosystem control-plane identity mismatch")
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
        {"RVIA_ROUTER", "SHADOW_GLASS", "GLASS_ONION", "ZYRA_CORE", "ZYRA_CLOUD", "XUNIA_CORE", "NXYZ"}.issubset(service_ids),
        "core service registry is incomplete",
    )

    agents = load_json(BH / "registry" / "agents.json")
    agent_ids = {item["id"] for item in agents["agents"]}
    require({"GPT_DOUG_MAX", "VIRGINIA", "VA3LM", "WAKEUP3LM"}.issubset(agent_ids), "agent registry is incomplete")

    mission = load_json(BH / "missions" / "mission.schema.json")
    mission_required = set(mission["required"])
    require(
        {"missionId", "requestedBy", "intent", "target", "classification", "approvalState", "evidence", "audit"}.issubset(mission_required),
        "mission envelope required fields are incomplete",
    )

    ontology = load_json(BH / "ontology" / "ontology.schema.json")
    object_types = set(ontology["properties"]["objects"]["items"]["enum"])
    relationship_types = set(ontology["properties"]["relationships"]["items"]["enum"])
    require({"Mission", "Agent", "Repository", "Service", "Evidence", "Policy"}.issubset(object_types), "ontology object vocabulary is incomplete")
    require({"EXECUTES", "PRODUCES", "GOVERNS", "IMPLEMENTS", "AUDITS"}.issubset(relationship_types), "ontology relationship vocabulary is incomplete")

    runtime = load_json(BH / "runtime" / "runtime-contract.json")
    require(runtime["controlPlane"] == "THE_BLACK_HOUSE_V1", "runtime control-plane identity mismatch")
    require(runtime["localRuntime"]["port"] == 8088, "VA3LM runtime port must remain 8088")
    require(runtime["localRuntime"]["healthPath"] == "/healthz", "VA3LM health contract mismatch")

    print("BLACK HOUSE CONTROL PLANE: GREEN")
    print(f"repositories={len(repo_ids)} services={len(service_ids)} agents={len(agent_ids)}")
    print("runtime_contract=BLACK_HOUSE_RUNTIME_V1 port=8088")


if __name__ == "__main__":
    main()
