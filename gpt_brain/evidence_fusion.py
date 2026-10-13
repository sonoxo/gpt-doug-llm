"""GPT-Doug evidence fusion: bounded, offline, provenance-aware cognitive review.

This software evaluates declared observations. It is not a general intelligence,
an authenticity oracle, a patent verifier, or a device/surveillance controller.
No model, network, remote API, autonomous action, or paid token is required.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from ai_killswitch import require_ai_allowed, status as ai_stop_status
from sensor_swarm.core import (
    ALLOWED_ENUMS, IDENT, SAFE_UNIT, Store, demo_specs, digest, load_policy, snapshot,
)
from sensor_swarm.ontology import export_graph, verify_export

REPORT_SCHEMA = "gpt-doug.cognitive-evidence-brief.v1"
MAX_GRAPH_BYTES = 1024 * 1024
MAX_NODES = 512
MAX_EDGES = 512
MAX_OBSERVATIONS = 128
MAX_RESULT_EVENTS = 48
MAX_QUESTION_CHARS = 512
HEX_ID = re.compile(r"^[a-f0-9]{64}$")
LOCATOR = re.compile(r"^[A-Za-z0-9_./:-]{1,128}$")
TOKEN = re.compile(r"[a-z0-9]+")
STOP = {"a", "an", "the", "is", "are", "were", "was", "it", "in", "on",
        "and", "or", "for", "to", "from", "of", "with", "me", "what",
        "how", "can", "we", "our", "data", "status", "show", "please"}

class InvalidEvidence(ValueError):
    """Input is structurally invalid or not authorized for this offline analysis."""

def _fail(message: str):
    raise InvalidEvidence(message)

def _terms(text: str) -> set[str]:
    return {word for word in TOKEN.findall(text.lower()) if len(word) >= 2 and word not in STOP}

def _exact_keys(value: Any, allowed: set[str], mandatory: set[str], kind: str):
    if type(value) is not dict or not mandatory <= value.keys() or value.keys() - allowed:
        _fail("invalid or unknown fields in " + kind)

def _identifier(text: Any, prefix: str):
    if not isinstance(text, str) or not text.startswith(prefix):
        _fail("invalid ontology identifier")
    suffix = text[len(prefix):]
    if prefix == "observation:":
        if not HEX_ID.fullmatch(suffix):
            _fail("invalid observation digest ID")
    elif not IDENT.fullmatch(suffix):
        _fail("invalid ontology identifier")
    return text

def _event_time(value: Any, now: datetime) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        _fail("invalid observation timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvidence("timestamp is not ISO 8601") from exc
    if dt.tzinfo is None:
        _fail("observation timestamp must be timezone-aware")
    dt = dt.astimezone(timezone.utc)
    if dt.year < 1970 or dt > now + timedelta(days=1):
        _fail("observation timestamp is out of bounds")
    return dt

def _value(value: Any):
    if type(value) in (int, float):
        if not math.isfinite(value) or abs(value) > 1e15:
            _fail("numeric observation exceeds allowed bounds")
    elif type(value) is bool:
        return
    elif type(value) is str and value in ALLOWED_ENUMS:
        return
    else:
        _fail("sensor value must be a safe scalar or approved status enum")

def read_graph(path: str | Path) -> dict[str, Any]:
    """Read an explicitly selected local JSON export, rejecting oversized/symlink files."""
    file = Path(path).expanduser()
    if file.is_symlink() or not file.is_file():
        _fail("graph must be a local regular file, not a symlink")
    if file.stat().st_size > MAX_GRAPH_BYTES:
        _fail("graph exceeds the one-megabyte input budget")
    with file.open("rb") as stream:
        raw = stream.read(MAX_GRAPH_BYTES + 1)
    if len(raw) > MAX_GRAPH_BYTES:
        _fail("graph exceeds the one-megabyte input budget")
    try:
        graph = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidEvidence("graph must contain valid UTF-8 JSON") from exc
    return graph

def validated_observations(graph: dict[str, Any], *, now: datetime | None = None):
    """Verify export structure and return sanitized observations with source lineage.

    SHA-256 equality proves only that JSON matches its own digest. It cannot
    authenticate the exporter, the sensor, the patent, or a scientific result.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        _fail("analysis clock must include a timezone")
    now = now.astimezone(timezone.utc)
    if type(graph) is not dict or set(graph) != {
        "schema", "source_schema", "read_only", "automatically_promoted",
        "official_patent_verified", "nodes", "edges", "sha256",
    }:
        _fail("unknown ontology export schema")
    if not isinstance(graph["sha256"], str) or not HEX_ID.fullmatch(graph["sha256"]):
        _fail("invalid graph digest")
    if not (isinstance(graph["nodes"], list) and isinstance(graph["edges"], list)):
        _fail("ontology graph nodes and edges must be lists")
    if len(graph["nodes"]) > MAX_NODES or len(graph["edges"]) > MAX_EDGES:
        _fail("ontology export exceeds research budget")
    if not verify_export(graph):
        _fail("ontology graph integrity or safety flags invalid")
    policy = load_policy()
    allowed_objects = set(policy["allowed_object_types"]) - set(policy["prohibited_object_types"])
    nodes: dict[str, dict[str, Any]] = {}
    observations: dict[str, dict[str, Any]] = {}
    for node in graph["nodes"]:
        if type(node) is not dict:
            _fail("ontology node must be an object")
        kind = node.get("kind")
        if kind == "sensor":
            _exact_keys(node, {"id", "kind", "adapter", "state"},
                        {"id", "kind", "state"}, kind)
            _identifier(node["id"], "sensor:")
            if node["state"] not in {"unknown", "healthy", "rejected"}:
                _fail("unexpected sensor state")
            if "adapter" in node and node["adapter"] not in {
                "biopineal", "synthetic", "host-health", "json", "jsonl", "csv",
            }:
                _fail("unknown sensor adapter")
        elif kind == "source":
            _exact_keys(node, {"id", "kind", "authenticity_verified", "classification"},
                        {"id", "kind", "authenticity_verified", "classification"}, kind)
            _identifier(node["id"], "source:")
            if node["authenticity_verified"] is not False:
                _fail("source authenticity must not be asserted by an unverified export")
            if node["classification"] not in {"public", "synthetic", "authorized_local"}:
                _fail("invalid source classification")
        elif kind == "observation":
            _exact_keys(node, {"id", "kind", "metric", "value", "unit",
                               "observed_at", "authorization_scope", "object_type",
                               "provenance", "source_verified"},
                        {"id", "kind", "metric", "value", "unit", "observed_at",
                         "authorization_scope", "object_type", "provenance",
                         "source_verified"}, kind)
            ident = _identifier(node["id"], "observation:")
            if not HEX_ID.fullmatch(ident[len("observation:"):]):
                _fail("invalid observation digest ID")
            if node["source_verified"] is not False:
                _fail("observation cannot claim independently authenticated source")
            if not isinstance(node["metric"], str) or not IDENT.fullmatch(node["metric"]):
                _fail("invalid metric label")
            if node["object_type"] not in allowed_objects:
                _fail("ontology object type prohibited")
            if not isinstance(node["authorization_scope"], str) or not IDENT.fullmatch(
                node["authorization_scope"]
            ):
                _fail("invalid declared authorization scope")
            if not isinstance(node["unit"], str) or not SAFE_UNIT.fullmatch(node["unit"]):
                _fail("invalid metric unit")
            _value(node["value"])
            observed = _event_time(node["observed_at"], now)
            provenance = node["provenance"]
            _exact_keys(provenance, {"adapter", "locator", "source_sha256",
                                     "authenticity_verified"},
                        {"adapter", "locator", "source_sha256", "authenticity_verified"},
                        "provenance")
            if provenance["authenticity_verified"] is not False:
                _fail("provenance cannot claim independent authentication")
            if provenance["adapter"] not in {"biopineal", "synthetic", "host-health",
                                             "json", "jsonl", "csv"}:
                _fail("unregistered provenance adapter")
            if not isinstance(provenance["locator"], str) or not LOCATOR.fullmatch(
                provenance["locator"]
            ):
                _fail("invalid source locator")
            if not isinstance(provenance["source_sha256"], str) or not HEX_ID.fullmatch(
                provenance["source_sha256"]
            ):
                _fail("invalid provenance hash")
            observations[ident] = {**node, "_parsed_at": observed}
        else:
            _fail("unexpected ontology node type")
        if node["id"] in nodes:
            _fail("duplicate ontology node identifier")
        nodes[node["id"]] = node
    if len(observations) > MAX_OBSERVATIONS:
        _fail("observation budget exceeded")
    links: dict[str, dict[str, str]] = defaultdict(dict)
    for edge in graph["edges"]:
        if type(edge) is not dict or set(edge) != {"from", "to", "type"}:
            _fail("unknown ontology relationship")
        if edge["from"] not in observations:
            _fail("edges may originate only from observations")
        relation = edge["type"]
        expected_type = {"OBSERVED_BY": "sensor", "DERIVED_FROM": "source"}.get(relation)
        if expected_type is None or edge["to"] not in nodes:
            _fail("invalid ontology relationship")
        if nodes[edge["to"]]["kind"] != expected_type:
            _fail("ontology relationship has wrong endpoint kind")
        if relation in links[edge["from"]]:
            _fail("ambiguous source/sensor link")
        links[edge["from"]][relation] = edge["to"]
    if any(set(links.get(ident, {})) != {"OBSERVED_BY", "DERIVED_FROM"}
           for ident in observations):
        _fail("observation is missing a source or sensor link")
    sanitized = []
    for ident, observation in observations.items():
        source_id = links[ident]["DERIVED_FROM"]
        sensor_id = links[ident]["OBSERVED_BY"]
        classification = nodes[source_id]["classification"]
        if observation["provenance"]["adapter"] == "synthetic" and classification != "synthetic":
            _fail("synthetic observations require synthetic classification")
        if observation["provenance"]["adapter"] == "biopineal" and (
            observation["object_type"] != "research_evidence" or classification != "public"
        ):
            _fail("BioPineal is unverified public research evidence, not a physical sensor")
        sanitized.append({
            "id": ident, "sensor_id": sensor_id, "source_id": source_id,
            "metric": observation["metric"], "value": observation["value"],
            "unit": observation["unit"], "observed_at": observation["observed_at"],
            "authorization_scope": observation["authorization_scope"],
            "object_type": observation["object_type"],
            "classification": classification,
            "source_sha256": observation["provenance"]["source_sha256"],
            "locator": observation["provenance"]["locator"],
            "source_authenticity": "UNVERIFIED",
            "_parsed_at": observation["_parsed_at"],
        })
    return sorted(sanitized, key=lambda row: (row["source_id"], row["metric"], row["observed_at"], row["id"]))

def _curate(events: list[dict[str, Any]], query: str, limit: int):
    terms = _terms(query)
    matches = []
    for item in events:
        search_terms = _terms(" ".join((item["sensor_id"], item["source_id"],
                                        item["metric"], item["object_type"])))
        score = len(terms & search_terms)
        if terms and score == 0:
            continue
        matches.append((score, item))
    matches.sort(key=lambda row: (-row[0], row[1]["source_id"],
                                  row[1]["metric"], row[1]["id"]))
    chosen = matches[:limit]
    evidence = []
    for match_score, item in chosen:
        evidence.append({k: v for k, v in item.items() if not k.startswith("_")}
                        | {"matching_terms": match_score})
    return {"matched_count": len(matches), "evidence": evidence,
            "query_terms": sorted(terms)}

def _compare(events: list[dict[str, Any]]):
    by_origin: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    by_metric: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set))
    for item in events:
        time = item["_parsed_at"].isoformat()
        value_repr = json.dumps(item["value"], sort_keys=True, separators=(",", ":"))
        by_origin[(item["source_id"], item["metric"], item["unit"], time)].add(value_repr)
        by_metric[(item["metric"], item["unit"], time)][item["source_id"]].add(value_repr)
    inconsistent = []
    for (source, metric, unit, time), values in sorted(by_origin.items()):
        if len(values) > 1:
            inconsistent.append({"type": "SAME_SOURCE_CONFLICT",
                                 "source_id": source, "metric": metric,
                                 "unit": unit, "observed_at": time,
                                 "distinct_values": len(values)})
    for (metric, unit, time), sources in sorted(by_metric.items()):
        if len(sources) > 1 and len(set.union(*sources.values())) > 1:
            inconsistent.append({"type": "CROSS_SOURCE_DISAGREEMENT",
                                 "source_ids": sorted(sources), "metric": metric,
                                 "unit": unit, "observed_at": time,
                                 "distinct_values": len(set.union(*sources.values()))})
    return inconsistent[:50]

def _freshness(events: list[dict[str, Any]], now: datetime, days: int):
    stale = [row for row in events if now - row["_parsed_at"] > timedelta(days=days)]
    return {"observations_reviewed": len(events), "stale": len(stale),
            "stale_event_ids": [e["id"] for e in stale[:20]],
            "freshness_is_authenticity": False}

def _govern(events: list[dict[str, Any]], excluded_local: int):
    kinds = {row["classification"] for row in events}
    return {"declared_source_count": len({row["source_id"] for row in events}),
            "source_authenticity_verified": False,
            "patent_identity_verified": False,
            "technology_use_rights_verified": False,
            "synthetic_evidence_present": "synthetic" in kinds,
            "local_records_excluded": excluded_local,
            "automatic_ontology_promotion": False,
            "external_actions_enabled": False,
            "model_inference_used": False}

def fuse(graph: dict[str, Any], question: str, *, include_local: bool = False,
         limit: int = 24, max_age_days: int = 30,
         now: datetime | None = None) -> dict[str, Any]:
    """Parallel bounded specialist analyses; preserve source-authentication uncertainty."""
    require_ai_allowed("cognitive evidence synthesis")
    if not isinstance(question, str) or not 3 <= len(question.strip()) <= MAX_QUESTION_CHARS:
        _fail("question length must be 3 to 512 characters")
    if type(limit) is not int or not 1 <= limit <= MAX_RESULT_EVENTS:
        _fail("result limit must be 1 to 48")
    if type(max_age_days) is not int or not 1 <= max_age_days <= 3650:
        _fail("freshness window must be 1 to 3650 days")
    if type(include_local) is not bool:
        _fail("include_local must be explicitly true or false")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    all_events = validated_observations(graph, now=now)
    excluded = sum(x["classification"] == "authorized_local" for x in all_events)
    selected = all_events if include_local else [
        x for x in all_events if x["classification"] != "authorized_local"
    ]
    # Each worker receives only a bounded list of validated scalar observations.
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="gpt-doug-curator") as pool:
        futures = {
            "evidence_curator": pool.submit(_curate, selected, question, limit),
            "consistency_critic": pool.submit(_compare, selected),
            "freshness_reviewer": pool.submit(_freshness, selected, now, max_age_days),
            "governance_auditor": pool.submit(_govern, selected, excluded if not include_local else 0),
        }
        findings = {name: futures[name].result() for name in sorted(futures)}
    relevant = findings["evidence_curator"]["evidence"]
    issues = []
    if not relevant:
        issues.append("NO_MATCHING_EVIDENCE")
    if findings["consistency_critic"]:
        issues.append("OBSERVATIONS_DISAGREE")
    if findings["freshness_reviewer"]["stale"]:
        issues.append("STALE_OBSERVATIONS_PRESENT")
    if findings["governance_auditor"]["synthetic_evidence_present"]:
        issues.append("SIMULATED_INPUT_PRESENT")
    issues.append("SOURCE_AUTHENTICITY_NOT_ESTABLISHED")
    if excluded and not include_local:
        issues.append("AUTHORIZED_LOCAL_DATA_REDACTED")
    recommendations = [
        "Verify material claims against independent primary sources before treating observations as facts.",
        "Require operator review before any memory promotion, real-world decision, or external action.",
    ]
    if "OBSERVATIONS_DISAGREE" in issues:
        recommendations.append("Reconcile conflicting readings and units before drawing conclusions.")
    if any(row["metric"] in ("official_patent_record_verified", "patent_rights_verified")
           and row["value"] is False for row in selected):
        recommendations.append("Confirm patent metadata and technology-use rights separately with primary sources.")
    summary = (
        f"{findings['evidence_curator']['matched_count']} relevant reported observations "
        f"from {len({item['source_id'] for item in selected})} declared sources; "
        "source authenticity not independently established."
    )
    report = {
        "schema": REPORT_SCHEMA, "mode": "OFFLINE_COGNITIVE_EVIDENCE_REVIEW",
        "question": question.strip(), "analyzed_at": now.isoformat(timespec="seconds"),
        "input_graph_sha256": graph["sha256"],
        "summary": summary, "evidence_status": "UNVERIFIED_REPORTED_OBSERVATIONS",
        "workers": findings, "issues": sorted(set(issues)),
        "next_review_steps": recommendations,
        "read_only": True, "no_network": True,
        "model_calls": 0, "external_actions": 0,
        "claim_of_superintelligence": False,
    }
    report["sha256"] = digest(report)
    require_ai_allowed("cognitive evidence review completion")
    return report

def verify_brief(value: Any) -> bool:
    """Replay integrity check, never source/authenticity verification."""
    if type(value) is not dict or set(value) != {
        "schema", "mode", "question", "analyzed_at", "input_graph_sha256",
        "summary", "evidence_status", "workers", "issues", "next_review_steps",
        "read_only", "no_network", "model_calls", "external_actions",
        "claim_of_superintelligence", "sha256",
    }:
        return False
    if value.get("schema") != REPORT_SCHEMA or value.get("read_only") is not True:
        return False
    if value.get("no_network") is not True or value.get("model_calls") != 0 or value.get("external_actions") != 0:
        return False
    if value.get("claim_of_superintelligence") is not False:
        return False
    if value.get("evidence_status") != "UNVERIFIED_REPORTED_OBSERVATIONS":
        return False
    return value.get("sha256") == digest({k: v for k, v in value.items() if k != "sha256"})

def build_demo_graph() -> dict[str, Any]:
    """Ephemeral fixture plus BioPineal research evidence; no external inputs."""
    with tempfile.TemporaryDirectory(prefix="gpt-doug-cognitive-demo-") as root:
        db = Store(Path(root) / "demo.sqlite3")
        try:
            db.write(snapshot(demo_specs()))
            return export_graph(db)
        finally:
            db.close()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Free, offline GPT-Doug cognitive evidence review")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Analyze synthetic and BioPineal demo evidence")
    demo.add_argument("--question", default="BioPineal patent evidence verification")
    brief = sub.add_parser("brief", help="Review an explicit local sensor ontology JSON export")
    brief.add_argument("--graph", required=True)
    brief.add_argument("--question", required=True)
    brief.add_argument("--include-local", action="store_true",
                       help="Explicitly include locally authorized records in output")
    brief.add_argument("--limit", type=int, default=24)
    brief.add_argument("--max-age-days", type=int, default=30)
    verify = sub.add_parser("verify", help="Check only local JSON report integrity")
    verify.add_argument("file")
    sub.add_parser("status", help="Display capability boundaries and cooperative AI stop status")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {
                "system": "GPT-DOUG-COGNITIVE-FUSION",
                "mode": "OFFLINE_RESEARCH",
                "local_only": True,
                "paid_tokens_required": False,
                "model_configured_or_inferred": False,
                "global_access_claimed": False,
                "ai_killswitch": ai_stop_status(),
            }
        elif args.command == "verify":
            result = {"integrity_verified": verify_brief(read_graph(args.file)),
                      "source_authenticity_verified": False}
        elif args.command == "demo":
            result = fuse(build_demo_graph(), args.question)
        else:
            result = fuse(read_graph(args.graph), args.question,
                          include_local=args.include_local, limit=args.limit,
                          max_age_days=args.max_age_days)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
        if args.command == "verify" and not result["integrity_verified"]:
            return 1
        return 0
    except (OSError, ValueError, PermissionError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__,
                          "message": str(exc)[:200]}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
