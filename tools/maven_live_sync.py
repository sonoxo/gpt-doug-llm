#!/usr/bin/env python3
"""Governed Maven/Foundry ontology export -> XUNIA Maven Ontology sync.

The sync is intentionally local/repository-first. It never calls Palantir APIs,
never embeds credentials, and only accepts exports whose envelope is explicitly
approved for ontology sync. Output is deterministic for a given approved export
so repeated processing is idempotent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

ALLOWED_ACTION_MODES = {"recommend", "simulate", "approved"}
ALLOWED_STATUSES = {"candidate", "verified"}
SCHEMA_VERSION = "maven-export/1.0"


class SyncError(ValueError):
    """Raised when an export violates the Maven Live Sync contract."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SyncError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SyncError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SyncError("top-level JSON value must be an object")
    return value


def _parse_iso8601(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SyncError(f"{field} is required")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SyncError(f"{field} must be ISO-8601") from exc
    return value.strip()


def _required_text(obj: dict[str, Any], key: str, scope: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SyncError(f"{scope}.{key} is required")
    return value.strip()


def _position(node_id: str) -> tuple[float, float]:
    digest = hashlib.sha256(node_id.encode("utf-8")).digest()
    lat_raw = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    lon_raw = int.from_bytes(digest[4:8], "big") / 0xFFFFFFFF
    return round(-70 + lat_raw * 140, 4), round(-180 + lon_raw * 360, 4)


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_link(raw: Any) -> list[str]:
    if isinstance(raw, list) and len(raw) == 3:
        source, target, relation = raw
    elif isinstance(raw, dict):
        source = raw.get("source")
        target = raw.get("target")
        relation = raw.get("relation") or raw.get("type")
    else:
        raise SyncError("each link must be [source,target,relation] or an object")
    values = (source, target, relation)
    if not all(isinstance(item, str) and item.strip() for item in values):
        raise SyncError("link source, target and relation must be non-empty strings")
    return [str(source).strip(), str(target).strip(), str(relation).strip().upper()]


def validate_export(export: dict[str, Any]) -> dict[str, Any]:
    if export.get("schemaVersion") != SCHEMA_VERSION:
        raise SyncError(f"schemaVersion must be {SCHEMA_VERSION}")

    source = export.get("source")
    approval = export.get("approval")
    if not isinstance(source, dict):
        raise SyncError("source object is required")
    if not isinstance(approval, dict):
        raise SyncError("approval object is required")

    source_system = _required_text(source, "system", "source")
    export_id = _required_text(source, "exportId", "source")
    source_uri = _required_text(source, "uri", "source")
    generated_at = _parse_iso8601(_required_text(source, "generatedAt", "source"), "source.generatedAt")

    if str(approval.get("status", "")).lower() != "approved":
        raise SyncError("approval.status must be approved")
    if approval.get("scope") != "ontology-sync":
        raise SyncError("approval.scope must be ontology-sync")
    approved_by = _required_text(approval, "approvedBy", "approval")
    approved_at = _parse_iso8601(_required_text(approval, "approvedAt", "approval"), "approval.approvedAt")

    nodes = export.get("nodes")
    links = export.get("links")
    if not isinstance(nodes, list) or not nodes:
        raise SyncError("nodes must be a non-empty array")
    if not isinstance(links, list):
        raise SyncError("links must be an array")

    normalized_nodes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in nodes:
        if not isinstance(raw, dict):
            raise SyncError("each node must be an object")
        node = deepcopy(raw)
        node_id = _required_text(node, "id", "node")
        if node_id in seen_ids:
            raise SyncError(f"duplicate node id in export: {node_id}")
        seen_ids.add(node_id)
        node["id"] = node_id
        node["label"] = _required_text(node, "label", f"node[{node_id}]")
        node["objectType"] = _required_text(node, "objectType", f"node[{node_id}]")
        node["type"] = str(node.get("type") or "knowledge").strip().lower()

        status = str(node.get("status") or "candidate").strip().lower()
        if status not in ALLOWED_STATUSES:
            raise SyncError(f"node[{node_id}].status must be candidate or verified")
        node["status"] = status

        confidence = node.get("confidence", 0.5)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise SyncError(f"node[{node_id}].confidence must be numeric")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise SyncError(f"node[{node_id}].confidence must be between 0 and 1")
        node["confidence"] = round(confidence, 6)

        if node["objectType"] == "Action":
            mode = str(node.get("mode") or "recommend").strip().lower()
            if mode not in ALLOWED_ACTION_MODES:
                raise SyncError(f"node[{node_id}].mode is not governed")
            node["mode"] = mode
            if mode == "approved" and not str(node.get("approvalId") or "").strip():
                raise SyncError(f"approved Action {node_id} requires approvalId")

        if not isinstance(node.get("lat"), (int, float)) or not isinstance(node.get("lon"), (int, float)):
            node["lat"], node["lon"] = _position(node_id)

        upstream = node.get("provenance") if isinstance(node.get("provenance"), dict) else {}
        node["provenance"] = {
            "sourceSystem": source_system,
            "sourceUri": source_uri,
            "exportId": export_id,
            "generatedAt": generated_at,
            "approvedBy": approved_by,
            "approvedAt": approved_at,
            "syncMethod": "maven-live-sync/1.0",
            "upstream": upstream,
        }
        normalized_nodes.append(node)

    normalized_links = [_normalize_link(link) for link in links]
    return {
        "source": {
            "system": source_system,
            "exportId": export_id,
            "uri": source_uri,
            "generatedAt": generated_at,
        },
        "approval": {
            "status": "approved",
            "scope": "ontology-sync",
            "approvedBy": approved_by,
            "approvedAt": approved_at,
        },
        "nodes": normalized_nodes,
        "links": normalized_links,
    }


def merge_graph(existing: dict[str, Any], normalized: dict[str, Any]) -> dict[str, Any]:
    graph = deepcopy(existing)
    graph.setdefault("meta", {})
    graph.setdefault("governance", {})
    graph.setdefault("nodes", [])
    graph.setdefault("links", [])
    graph.setdefault("objectTypes", [])
    graph.setdefault("relationTypes", [])

    current_nodes = graph["nodes"]
    if not isinstance(current_nodes, list):
        raise SyncError("target graph nodes must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for node in current_nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise SyncError("target graph contains invalid node")
        if node["id"] in by_id:
            raise SyncError(f"target graph contains duplicate node id: {node['id']}")
        by_id[node["id"]] = node

    for node in normalized["nodes"]:
        by_id[node["id"]] = node
    merged_nodes = [by_id[key] for key in sorted(by_id)]

    link_set: set[tuple[str, str, str]] = set()
    for raw in [*graph["links"], *normalized["links"]]:
        source, target, relation = _normalize_link(raw)
        link_set.add((source, target, relation))

    ids = set(by_id)
    for source, target, relation in link_set:
        if source not in ids or target not in ids:
            raise SyncError(f"broken link {source} -[{relation}]-> {target}")

    approval_ids = {node["id"] for node in merged_nodes if node.get("objectType") == "Approval"}
    for node in merged_nodes:
        if node.get("objectType") == "Action" and node.get("mode") == "approved":
            if node.get("approvalId") not in approval_ids:
                raise SyncError(f"approved Action {node['id']} references missing Approval")

    object_types = sorted({str(node.get("objectType")) for node in merged_nodes if node.get("objectType")})
    relation_types = sorted({relation for _, _, relation in link_set})

    source = normalized["source"]
    approval = normalized["approval"]
    graph["nodes"] = merged_nodes
    graph["links"] = [list(item) for item in sorted(link_set)]
    graph["objectTypes"] = object_types
    graph["relationTypes"] = relation_types
    graph["meta"]["liveSync"] = {
        "version": "1.0",
        "lastExportId": source["exportId"],
        "lastSourceSystem": source["system"],
        "lastSourceUri": source["uri"],
        "sourceGeneratedAt": source["generatedAt"],
        "approvedBy": approval["approvedBy"],
        "approvedAt": approval["approvedAt"],
        "graphFingerprint": _fingerprint({"nodes": merged_nodes, "links": graph["links"]}),
    }
    graph["governance"]["actionModes"] = ["recommend", "simulate", "approved"]
    graph["governance"]["provenanceRequired"] = True
    graph["governance"]["humanApprovalRequiredForApprovedMode"] = True
    graph["governance"]["autonomousDisruptiveActions"] = False
    return graph


def update_audit(existing: dict[str, Any], normalized: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    audit = deepcopy(existing) if isinstance(existing, dict) else {}
    records = audit.get("records")
    if not isinstance(records, list):
        records = []
    export_id = normalized["source"]["exportId"]
    if not any(isinstance(item, dict) and item.get("exportId") == export_id for item in records):
        records.append({
            "exportId": export_id,
            "sourceSystem": normalized["source"]["system"],
            "sourceUri": normalized["source"]["uri"],
            "generatedAt": normalized["source"]["generatedAt"],
            "approvedBy": normalized["approval"]["approvedBy"],
            "approvedAt": normalized["approval"]["approvedAt"],
            "nodeCount": len(normalized["nodes"]),
            "linkCount": len(normalized["links"]),
            "graphFingerprint": graph["meta"]["liveSync"]["graphFingerprint"],
        })
    records.sort(key=lambda item: (str(item.get("approvedAt", "")), str(item.get("exportId", ""))))
    return {"version": "maven-sync-audit/1.0", "records": records}


def _dump(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def sync(input_path: Path, target_path: Path, audit_path: Path, *, check: bool = False) -> dict[str, Any]:
    normalized = validate_export(_load(input_path))
    existing = _load(target_path) if target_path.exists() else {}
    existing_audit = _load(audit_path) if audit_path.exists() else {}
    graph = merge_graph(existing, normalized)
    audit = update_audit(existing_audit, normalized, graph)

    graph_text = _dump(graph)
    audit_text = _dump(audit)
    graph_changed = not target_path.exists() or target_path.read_text(encoding="utf-8") != graph_text
    audit_changed = not audit_path.exists() or audit_path.read_text(encoding="utf-8") != audit_text

    if not check:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        if graph_changed:
            target_path.write_text(graph_text, encoding="utf-8")
        if audit_changed:
            audit_path.write_text(audit_text, encoding="utf-8")

    return {
        "ok": True,
        "exportId": normalized["source"]["exportId"],
        "sourceSystem": normalized["source"]["system"],
        "nodesImported": len(normalized["nodes"]),
        "linksImported": len(normalized["links"]),
        "graphNodes": len(graph["nodes"]),
        "graphLinks": len(graph["links"]),
        "graphChanged": graph_changed,
        "auditChanged": audit_changed,
        "checkOnly": check,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync an approved Maven/Foundry ontology export")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--target", type=Path, default=Path("docs/maven-ontology/ontology.json"))
    parser.add_argument("--audit", type=Path, default=Path("docs/maven-ontology/sync-log.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = sync(args.input, args.target, args.audit, check=args.check)
    except SyncError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
