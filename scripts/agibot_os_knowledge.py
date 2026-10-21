#!/usr/bin/env python3
"""Offline, source-grounded AGIBOT Link-U OS / X1 knowledge explorer.

No ROS 2 network access, AimRT RPC, dependency installation, model training,
physical robot commands, or hardware deployment. Only reads a versioned JSON
reference file in this repository.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "foundry" / "ontology" / "agibot-link-u-os-ontology.json"
SCHEMA = "xunia.embodied-os.public-reference.v1"
MODE = "READ_ONLY_SOURCE_GROUNDED_REFERENCE"
PINNED_REPOSITORIES = {
    "Link-U-OS/Link-U-OS": "64ac7b08dd609dfb463310945856419be470315a",
    "AgibotTech/agibot_x1_infer": "9e0b818804d644fb9c9663e932dd33b03b24dfa4",
    "AgibotTech/agibot_x1_train": "e6651b9ab843fd1b1be70c087bfb7e8b28e44ccd",
}
COMMANDS = frozenset({"status", "graph", "search", "show", "doctor"})
REQUIRED_GUARDRAILS = {
    "sourceDataNotExecutable": True,
    "noExternalNetworkAtRuntime": True,
    "noSubmoduleExecution": True,
    "noAutomaticDependencyInstall": True,
    "noModelWeightsImported": True,
    "noTrainingExecuted": True,
    "noHardwareControl": True,
    "noTeleoperation": True,
    "noRobotDeployment": True,
    "noMilitaryOrWeaponIntegration": True,
    "noAffiliationOrEndorsementClaim": True,
    "licenseReviewRequiredBeforeCodeReuse": True,
    "separateSubmoduleLicenseReviewRequired": True,
    "safetyReviewRequiredBeforeHardwareUse": True,
    "humanReviewRequiredBeforePromotion": True,
    "simulatorFirstForFutureWork": True,
    "operationalAuthority": "none",
    "sourceCoverageClaim": "LIMITED_DOCUMENTATION_REVIEW",
}
VALID_FAMILIES = frozenset({"link_u_os", "agibot_x1", "shared"})


def read() -> dict[str, Any]:
    value = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("ontology root must be an object")
    return value


def validate(data: Any) -> list[str]:
    """Fail-closed structural, provenance, separation, and authority checks."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["ontology root must be an object"]
    if data.get("schema") != SCHEMA:
        errors.append("schema mismatch")
    if data.get("id") != "AGIBOT_LINK_U_OS_AND_X1_PUBLIC_REFERENCE":
        errors.append("reference ID mismatch")
    if data.get("mode") != MODE:
        errors.append("read-only reference mode required")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("observedDate", ""))):
        errors.append("observedDate must be ISO calendar date")

    repositories = data.get("upstreamRepositories")
    if not isinstance(repositories, list) or len(repositories) != 3:
        errors.append("three pinned upstream repositories required")
        repositories = []
    repo_names: set[str] = set()
    for repository in repositories:
        if not isinstance(repository, dict):
            errors.append("repository must be an object")
            continue
        name = repository.get("repository")
        if name in repo_names:
            errors.append(f"duplicate repository: {name}")
        repo_names.add(name)
        if PINNED_REPOSITORIES.get(name) != repository.get("headCommit"):
            errors.append(f"unpinned or unexpected repository: {name}")
        if not repository.get("role") or not repository.get("licenseAtRepositoryRoot"):
            errors.append(f"repository missing provenance or license status: {name}")
    if repo_names != set(PINNED_REPOSITORIES):
        errors.append("source repository set drifted")

    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a nonempty list")
        sources = []
    source_ids: set[str] = set()
    for src in sources:
        if not isinstance(src, dict):
            errors.append("source must be an object")
            continue
        sid = src.get("id")
        if not isinstance(sid, str) or not sid or sid in source_ids:
            errors.append(f"missing or duplicate source ID: {sid!r}")
        source_ids.add(sid)
        url = src.get("url")
        if not isinstance(url, str) or not url.startswith("https://") or "?" in url:
            errors.append(f"source must have stable https URL without request tokens: {sid}")
        if not src.get("note"):
            errors.append(f"source missing scope note: {sid}")
        kind = src.get("kind")
        if kind == "pinned_upstream_file":
            repository = src.get("repository")
            sha = PINNED_REPOSITORIES.get(repository)
            if not sha or src.get("commit") != sha:
                errors.append(f"source commit is not pinned: {sid}")
            if not isinstance(url, str) or not url.startswith(
                f"https://github.com/{repository}/blob/{sha}/"
            ):
                errors.append(f"source URL does not match commit: {sid}")
        elif kind != "official_vendor_page":
            errors.append(f"source is of unsupported provenance type: {sid}")
    if {"agibot-open-docs", "agibot-link-u-page", "linku-readme", "x1-infer-readme", "x1-train-readme"} - source_ids:
        errors.append("required official/reference sources missing")

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a nonempty list")
        nodes = []
    node_ids: set[str] = set()
    families: dict[str, str] = {}
    for node in nodes:
        if not isinstance(node, dict):
            errors.append("node must be an object")
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or not nid or nid in node_ids:
            errors.append(f"missing or duplicate node ID: {nid!r}")
        node_ids.add(nid)
        if node.get("family") not in VALID_FAMILIES:
            errors.append(f"invalid family: {nid}")
        families[str(nid)] = node.get("family")
        if node.get("claimClass") != "SOURCE_DOCUMENTED":
            errors.append(f"node must be source-documented: {nid}")
        if not all(isinstance(node.get(k), str) and node[k] for k in ("kind", "label", "description")):
            errors.append(f"node description incomplete: {nid}")
        if not isinstance(node.get("tags"), list) or not all(isinstance(x, str) for x in node["tags"]):
            errors.append(f"node tags malformed: {nid}")
        evidence = node.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(s not in source_ids for s in evidence):
            errors.append(f"node has missing/unknown evidence: {nid}")
    if families.get("linku-os") != "link_u_os" or families.get("x1-platform") != "agibot_x1":
        errors.append("Link-U OS A2 and X1 families must stay separate")

    edges = data.get("edges")
    if not isinstance(edges, list) or not edges:
        errors.append("edges must be a nonempty list")
        edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append("edge must be an object")
            continue
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            errors.append(f"edge has dangling endpoint: {edge}")
        if not isinstance(edge.get("relation"), str) or not edge["relation"]:
            errors.append("edge missing relation")
        evidence = edge.get("evidence")
        if not isinstance(evidence, list) or not evidence or any(s not in source_ids for s in evidence):
            errors.append(f"edge has missing/unknown evidence: {edge.get('relation')}")

    coverage = data.get("sourceCoverage")
    if not isinstance(coverage, dict):
        errors.append("source coverage required")
    elif coverage.get("independentlyBenchmarked") is not False or coverage.get("liveConnected") is not False:
        errors.append("source coverage cannot claim live integration or benchmarks")

    proposal = data.get("gptDougIntegrationProposal")
    if not isinstance(proposal, dict):
        errors.append("integration proposal required")
    else:
        if proposal.get("status") != "DESIGN_ONLY_NOT_IMPLEMENTED":
            errors.append("integration must remain design-only")
        for field in ("simulatorConnected", "hardwareConnected", "robotCommandsEnabled"):
            if proposal.get(field) is not False:
                errors.append(f"{field} must be false")
        if proposal.get("humanApprovalRequiredForExpansion") is not True:
            errors.append("future expansion requires human approval")

    actions = data.get("actions")
    if not isinstance(actions, list):
        errors.append("actions must be a list")
        actions = []
    seen_actions: set[str] = set()
    for action in actions:
        if not isinstance(action, dict):
            errors.append("action must be an object")
            continue
        name = action.get("name")
        if name in seen_actions:
            errors.append(f"duplicate action: {name}")
        seen_actions.add(name)
        if (action.get("readOnly") is not True
                or action.get("networkEgress") is not False
                or action.get("externalMutation") is not False
                or action.get("robotControl") is not False):
            errors.append(f"non-read-only action rejected: {name}")
    if seen_actions != COMMANDS:
        errors.append("action inventory drifted")

    guardrails = data.get("guardrails")
    if not isinstance(guardrails, dict):
        errors.append("guardrails required")
    else:
        for key, expected in REQUIRED_GUARDRAILS.items():
            if guardrails.get(key) != expected:
                errors.append(f"guardrail {key} must equal {expected!r}")
    return errors


def matches(data: dict[str, Any], query: str, limit: int = 8) -> list[dict[str, Any]]:
    terms = {t for t in re.findall(r"[a-z0-9_]+", query.lower()) if len(t) >= 2}
    if not terms:
        return []
    sources = {s["id"]: s for s in data["sources"]}
    results: list[dict[str, Any]] = []
    for node in data["nodes"]:
        title = node["label"].lower()
        tags = " ".join(node["tags"]).lower()
        description = node["description"].lower()
        score = 5 * len(terms & set(re.findall(r"[a-z0-9_]+", title)))
        score += 3 * len(terms & set(re.findall(r"[a-z0-9_]+", tags)))
        score += len(terms & set(re.findall(r"[a-z0-9_]+", description)))
        if score:
            results.append({
                "score": score, "id": node["id"], "label": node["label"],
                "family": node["family"], "description": node["description"],
                "source_urls": [sources[s]["url"] for s in node["evidence"]],
            })
    return sorted(results, key=lambda x: (-x["score"], x["id"]))[:max(1, limit)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agibot-os", description=__doc__)
    parser.add_argument("command", choices=sorted(COMMANDS), nargs="?", default="status")
    parser.add_argument("item", nargs="?", help="node ID or quoted query")
    parser.add_argument("--json", action="store_true", help="show machine-readable output")
    parser.add_argument("--top", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        data = read()
        errors = validate(data)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"AGIBOT KNOWLEDGE: NO-GO: {exc}", file=sys.stderr)
        return 1

    if args.command == "doctor":
        if errors:
            print("AGIBOT KNOWLEDGE DOCTOR: NO-GO")
            for error in errors:
                print(f" - {error}")
            return 1
        print("AGIBOT KNOWLEDGE DOCTOR: GREEN")
        print("Sources:", len(data["sources"]), "Nodes:", len(data["nodes"]), "Edges:", len(data["edges"]))
        print("Robot connectivity: DISABLED | Mode: READ ONLY")
        return 0

    if errors:
        print("AGIBOT KNOWLEDGE: NO-GO; run doctor", file=sys.stderr)
        return 1

    if args.command == "status":
        value = {
            "id": data["id"], "mode": data["mode"], "observedDate": data["observedDate"],
            "sources": len(data["sources"]), "nodes": len(data["nodes"]), "edges": len(data["edges"]),
            "pinned_repositories": data["upstreamRepositories"],
            "integration_status": data["gptDougIntegrationProposal"]["status"],
            "hardware_connected": False, "simulator_connected": False,
        }
        if args.json:
            print(json.dumps(value, indent=2))
        else:
            print("GPT-DOUG // AGIBOT OS SOURCE KNOWLEDGE")
            for key, item in value.items():
                print(f"{key}: {item}")
        return 0

    if args.command == "graph":
        if args.json:
            print(json.dumps({"nodes": data["nodes"], "edges": data["edges"]}, indent=2))
        else:
            print("digraph agibot_reference {")
            for node in data["nodes"]:
                label = node["label"].replace('"', r'\"')
                print(f'  "{node["id"]}" [label="{label}"];')
            for edge in data["edges"]:
                print(f'  "{edge["from"]}" -> "{edge["to"]}" [label="{edge["relation"]}"];')
            print("}")
        return 0

    if not args.item:
        parser.error(f"{args.command} requires a node ID or query")
    if args.command == "search":
        result = {"query": args.item, "results": matches(data, args.item, args.top)}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for row in result["results"]:
                print(f'{row["score"]:>3} {row["id"]}: {row["label"]}')
                print(f'    {row["source_urls"][0]}')
        return 0

    if args.command == "show":
        node = next((n for n in data["nodes"] if n["id"] == args.item), None)
        if node is None:
            print(f"AGIBOT KNOWLEDGE: unknown node {args.item}", file=sys.stderr)
            return 2
        source_index = {s["id"]: s for s in data["sources"]}
        print(json.dumps({"node": node, "sources": [source_index[s] for s in node["evidence"]]}, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
