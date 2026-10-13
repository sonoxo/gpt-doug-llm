"""Versioned, read-only ontology projection for a validated ATAK-Maps catalog."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def build_ontology(catalog: dict) -> dict[str, Any]:
    """Map provider/source/category/format/policy into graph nodes and edges.

    This graph describes documentation relationships only. It cannot infer
    device connectivity, authorization, tile availability or tactical status.
    """
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str], dict] = {}

    def node(key: str, kind: str, label: str, **properties: Any) -> None:
        nodes.setdefault(key, {"id": key, "type": kind, "label": label, "properties": properties})

    def edge(a: str, b: str, relation: str) -> None:
        edges[(a, b, relation)] = {"from": a, "to": b, "relationship": relation}

    source = catalog["source"]
    node("repo:atak-maps", "SourceRepository", "sonoxo/ATAK-Maps",
         sha=source.get("commit_sha"), digest=source.get("catalog_sha256"),
         license=source.get("license_notice"), provenance="GITHUB_LOCAL_CHECKOUT")
    node("viewer:gpt-doug-tak-geo", "GeospatialViewer", "GPT-Doug TAK-GEO",
         mode="LOCAL_OFFLINE", tak_server_connected=False, network_default=False)
    edge("viewer:gpt-doug-tak-geo", "repo:atak-maps", "READS_DOCUMENTED_CATALOG")

    for item in catalog["entries"]:
        layer = "source:" + item["id"]
        provider = "provider:" + item["provider"].lower()
        category = "category:" + item["category"].lower().replace(" ", "_")
        format_key = "format:" + item["source_type"].lower().replace("-", "_")
        policy = "policy:" + item["policy"].lower()
        node(layer, "MapSource", item["name"], path=item["path"],
             xml_sha256=item["xml_sha256"], overlay=item["overlay"],
             min_zoom=item["min_zoom"], max_zoom=item["max_zoom"],
             access_policy=item["policy"])
        node(provider, "MapProvider", item["provider"])
        node(category, "MapCategory", item["category"])
        node(format_key, "MapSourceFormat", item["source_type"])
        node(policy, "MapAccessPolicy", item["policy"])
        edge("repo:atak-maps", layer, "DOCUMENTS")
        edge(layer, provider, "PUBLISHED_BY")
        edge(layer, category, "HAS_CATEGORY")
        edge(layer, format_key, "USES_FORMAT")
        edge(layer, policy, "REQUIRES_ACCESS_POLICY")
        if item["policy"] == "OPT_IN_USGS_PREVIEW":
            edge("viewer:gpt-doug-tak-geo", layer, "OPTIONAL_OPERATOR_OPT_IN_PREVIEW")
    result = {
        "schema": "xunia.tak.maps-ontology.v1",
        "authority": "READ_ONLY_DOCUMENTATION_GRAPH",
        "source_repository": source["repository"],
        "source_commit": source.get("commit_sha"),
        "source_catalog_sha256": source["catalog_sha256"],
        "runtime_connections": 0,
        "no_live_device_inference": True,
        "nodes": sorted(nodes.values(), key=lambda v: v["id"]),
        "edges": [edges[key] for key in sorted(edges)],
    }
    canonical = json.dumps({"nodes": result["nodes"], "edges": result["edges"]}, sort_keys=True, separators=(",", ":"))
    result["graph_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return result
