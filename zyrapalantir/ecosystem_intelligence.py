"""Offline, provenance-first transcription of a user-provided ecosystem diagram.

No Palantir tenant access, network requests, credential handling, or external writes.
Every grouping is an unverified statement about the *graphic*, not the world.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

SOURCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "agency_cloud"
    / "static"
    / "palantir-ecosystem-data.json"
)
CLAIM_STATUS = "unverified_visual_depiction"
VISUAL_CATEGORIES = {
    "economic_partners",
    "reactionary_politics",
    "investors_clients",
    "unspecified",
}


class DiagramValidationError(ValueError):
    """Raised when provenance or fail-closed validation is violated."""


def load_diagram(path: Optional[Path] = None) -> dict[str, Any]:
    """Read and validate a *local* diagram transcription (never remote URLs)."""
    candidate = Path(path) if path is not None else SOURCE_PATH
    with candidate.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    validate_diagram(document)
    return document


def validate_diagram(document: dict[str, Any]) -> None:
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise DiagramValidationError("unsupported diagram schema")
    source = document.get("source")
    controls = document.get("controls")
    if not isinstance(source, dict) or not isinstance(controls, dict):
        raise DiagramValidationError("missing source provenance or controls")
    digest = source.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        char not in "0123456789abcdef" for char in digest
    ):
        raise DiagramValidationError("source must include a lowercase SHA-256 digest")
    if source.get("verification_status") != "unverified":
        raise DiagramValidationError("the graphic cannot be promoted to verified evidence")
    if controls != {
        "mode": "offline_read_only",
        "third_party_access": False,
        "external_writes": False,
        "independent_verification": False,
    }:
        raise DiagramValidationError("diagram controls cannot grant authority")
    groups = document.get("groups")
    if not isinstance(groups, list) or not groups:
        raise DiagramValidationError("groups must be a nonempty list")
    seen_groups: set[str] = set()
    seen_members: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            raise DiagramValidationError("group must be an object")
        group_id = group.get("id")
        label = group.get("label")
        members = group.get("members")
        if (
            not isinstance(group_id, str)
            or not group_id
            or not all(c.islower() or c.isdigit() or c == "_" for c in group_id)
            or group_id in seen_groups
            or not isinstance(label, str)
            or not label.strip()
            or group.get("visual_category") not in VISUAL_CATEGORIES
            or not isinstance(members, list)
            or not members
        ):
            raise DiagramValidationError("invalid or duplicate group")
        seen_groups.add(group_id)
        for member in members:
            if not isinstance(member, str) or not member.strip():
                raise DiagramValidationError("empty or invalid group member")
            marker = member.casefold()
            if marker in seen_members or marker == "palantir":
                raise DiagramValidationError("duplicate or reserved entity")
            seen_members.add(marker)


def graph_snapshot(path: Optional[Path] = None) -> dict[str, Any]:
    """Create a typed graph with strictly unverified, non-authoritative links."""
    doc = load_diagram(path)
    nodes: list[dict[str, Any]] = [
        {"id": "palantir", "label": "Palantir", "type": "diagram_focus"}
    ]
    links: list[dict[str, Any]] = []
    for group in doc["groups"]:
        group_id = f"group:{group['id']}"
        nodes.append({
            "id": group_id,
            "label": group["label"],
            "type": "diagram_group",
            "visual_category": group["visual_category"],
        })
        links.append({
            "source": "palantir", "target": group_id,
            "type": "graphic_layout_context", "claim_status": CLAIM_STATUS,
            "source_id": doc["source"]["id"],
        })
        for number, member in enumerate(group["members"]):
            entity_id = f"entity:{group['id']}:{number}"
            nodes.append({
                "id": entity_id, "label": member,
                "type": "named_in_diagram", "group": group["id"],
            })
            links.append({
                "source": group_id, "target": entity_id,
                "type": "graphic_group_membership", "claim_status": CLAIM_STATUS,
                "source_id": doc["source"]["id"],
            })
    return {
        "graph_id": doc["graph_id"],
        "source": doc["source"],
        "controls": doc["controls"],
        "disclaimer": doc["disclaimer"],
        "nodes": nodes,
        "links": links,
        "metrics": {
            "groups": len(doc["groups"]),
            "depicted_entities": len(nodes) - len(doc["groups"]) - 1,
            "depicted_links": len(links),
            "independently_verified_links": 0,
        },
    }


def ontology_export(path: Optional[Path] = None) -> dict[str, Any]:
    """Return review-only records, not a write operation or tenant import."""
    graph = graph_snapshot(path)
    return {
        "format": "gpt_doug_review_only_ontology_projection_v1",
        "import_executed": False,
        "execution_authorized": False,
        "source": graph["source"],
        "objects": graph["nodes"],
        "links": graph["links"],
        "warning": graph["disclaimer"],
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Palantir diagram intelligence")
    parser.add_argument("command", choices=("status", "graph", "ontology", "verify"))
    parser.add_argument("--file", type=Path, help="optional local JSON file")
    args = parser.parse_args(argv)
    if args.command == "verify":
        doc = load_diagram(args.file)
        result = {"valid": True, "source_id": doc["source"]["id"], "verified": False}
    elif args.command == "status":
        graph = graph_snapshot(args.file)
        result = {"metrics": graph["metrics"], "controls": graph["controls"]}
    elif args.command == "ontology":
        result = ontology_export(args.file)
    else:
        result = graph_snapshot(args.file)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
