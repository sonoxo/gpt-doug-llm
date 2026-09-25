"""Reproducible synthetic experiment with explicit expected outcomes."""
from .approval import ApprovalGate, digest
from .repair import plan
from .reconcile import reconcile
from .lineage import anchor, audit


def run():
    snapshot = {"mission": "synthetic-test", "action": "test-only",
                "code": {"worker": digest("v1")}, "data": {"input": digest("sample")},
                "policy": {"policy": digest("v1")}}
    gate = ApprovalGate(":memory:", ["demo-operator"])
    try:
        token = gate.issue(snapshot, "demo-operator", 100)
        changed = {**snapshot, "code": {"worker": digest("v2")}}
        rejected_change = not gate.consume(token, changed, 101)
        admitted_original = gate.consume(token, snapshot, 102)
        rejected_replay = not gate.consume(token, snapshot, 103)
    finally:
        gate.close()
    deps = {"source": [], "index": ["source"], "report": ["index"], "unrelated": []}
    repair = plan(deps, ["source"], {k: ["test_" + k] for k in deps}, {k: "v1" for k in deps})
    merge = reconcile({"a": 1, "b": 1}, {"a": 2, "b": 1}, {"a": 1, "b": 2})
    conflict = reconcile({"a": 1}, {"a": 2}, {"a": 3})
    docs = {"doc": "Verified sample passage."}
    citation = anchor("doc", docs["doc"], 0, 8)
    claims = {"claim": {"citations": [citation]},
              "derived": {"citations": [citation], "depends_on": ["claim"]}}
    before, after = audit(claims, docs), audit(claims, {"doc": "Changed sample passage."})
    checks = {"changed_snapshot_rejected": rejected_change,
              "original_admitted_once": admitted_original, "replay_rejected": rejected_replay,
              "transitive_impact": repair["affected"] == ["index", "report", "source"],
              "disjoint_changes_merged": merge["candidate"] == {"a": 2, "b": 2},
              "conflict_blocks_apply": not conflict["apply_allowed"],
              "original_anchors_valid": not before["invalidated"],
              "changed_source_invalidates_claims": after["invalidated"] == ["claim", "derived"]}
    return {"synthetic": True, "checks": checks, "passed": all(checks.values()),
            "repair": repair, "merge": merge, "lineage_after_change": after}
