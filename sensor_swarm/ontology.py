"""Provenance-preserving, export-only observation graph for GPT-Doug ontology review.

Exports do not write to, authorize, or automatically promote the global ontology.
"""
from __future__ import annotations

from .core import SCHEMA, canonical, digest

def export_graph(store, limit=100):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("ontology export limit must be between 1 and 200")
    status = store.status(limit)
    nodes, edges = {}, {}
    for sensor in status["sensors"]:
        sid = "sensor:" + sensor["id"]
        nodes[sid] = {"id": sid, "kind": "sensor", "adapter": sensor["adapter"],
                      "state": sensor["status"]}
    for event in status["events"]:
        sid = "sensor:" + event["sensor_id"]
        oid = "observation:" + event["id"]
        source_id = "source:" + event["source_id"]
        nodes.setdefault(sid, {"id": sid, "kind": "sensor", "state": "unknown"})
        nodes[source_id] = {"id": source_id, "kind": "source",
                            "authenticity_verified": False,
                            "classification": event["classification"]}
        nodes[oid] = {"id": oid, "kind": "observation", "metric": event["metric"],
                      "value": event["value"], "unit": event["unit"],
                      "observed_at": event["observed_at"],
                      "authorization_scope": event["authorization_scope"],
                      "object_type": event["object_type"],
                      "provenance": event["provenance"],
                      "source_verified": False}
        for dest, relation in ((sid, "OBSERVED_BY"), (source_id, "DERIVED_FROM")):
            key = (oid, dest, relation)
            edges[key] = {"from": oid, "to": dest, "type": relation}
    graph = {"schema": "gpt-doug.sensor-ontology-export.v1",
             "source_schema": SCHEMA, "read_only": True,
             "automatically_promoted": False, "official_patent_verified": False,
             "nodes": [nodes[k] for k in sorted(nodes)],
             "edges": [edges[k] for k in sorted(edges)]}
    graph["sha256"] = digest(graph)
    return graph

def verify_export(data):
    if not isinstance(data, dict) or "sha256" not in data:
        return False
    prepared = {k: v for k, v in data.items() if k != "sha256"}
    ids = {n.get("id") for n in data.get("nodes", []) if isinstance(n, dict)}
    return (
        data["sha256"] == digest(prepared)
        and data.get("read_only") is True
        and data.get("automatically_promoted") is False
        and data.get("official_patent_verified") is False
        and all(e.get("from") in ids and e.get("to") in ids
                for e in data.get("edges", []) if isinstance(e, dict))
    )
