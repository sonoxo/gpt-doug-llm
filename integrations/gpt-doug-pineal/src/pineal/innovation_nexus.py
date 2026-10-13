"""BioPineal Patent Evidence Nexus: local provenance and governance, not chemistry.

Reads a single user-supplied USPTO excerpt from an approved local JSONL
metadata fixture and checks a typed ontology. Can import metadata into the
existing PINEAL SQLite index ONLY after explicit --commit. Never fetches a
webpage, executes a patent process, or claims any external verification.
"""
from __future__ import annotations

import hashlib
import html
import json
import sys
import time
from pathlib import Path
from typing import Any

from .patents import load_records
from .store import PinealStore

PROJECT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT / "examples" / "patents" / "user-supplied-us12760393b1.jsonl"
ONTOLOGY = PROJECT / "ontology" / "lithium_nexus_v1.json"
PATENT_ID = "US12760393B1"
OWNER = "PolyPlus Battery Company"
PROVENANCE = "USER_PROVIDED_USPTO_PASTED_EXCERPT_UNVERIFIED_BY_INDEPENDENT_LOOKUP"
REQUIRED_NODES = frozenset({
    "publication", "assignee", "brine", "recycled_lithium", "selective_membrane",
    "laminate", "lithium_hydroxide", "hydrogen_gas", "chlorine_gas",
    "flammability", "toxicity", "corrosion", "patent_review", "process_safety",
    "provider_check", "pineal_store", "peace_truth"
})
REQUIRED_EDGES = frozenset({
    ("publication", "assignee", "attributed_to"),
    ("publication", "hydrogen_gas", "mentions_possible_coproduct"),
    ("publication", "chlorine_gas", "mentions_possible_coproduct"),
    ("hydrogen_gas", "flammability", "requires_risk_review"),
    ("chlorine_gas", "toxicity", "requires_risk_review"),
    ("publication", "patent_review", "requires_human_review"),
    ("publication", "provider_check", "requires_external_verification"),
    ("pineal_store", "peace_truth", "cannot_promote_impact"),
})
ALLOWED_KINDS = frozenset({
    "patent_document", "organization", "material_source", "technology_concept",
    "material_output", "potential_coproduct", "hazard", "approval_required",
    "verification_required", "software_component", "separate_boundary"
})
ALLOWED_RELATIONS = frozenset({
    "attributed_to", "describes_source", "describes", "discloses_possible_product",
    "mentions_possible_coproduct", "requires_risk_review", "requires_human_review",
    "requires_external_verification", "indexable_as_metadata", "cannot_promote_impact"
})
CLASSIFICATION_KEYWORDS = {
    "lithium": ("lithium", "li-ion", "lioh"),
    "membrane": ("membrane", "ceramic", "laminate"),
    "brine": ("brine", "geothermal", "oilfield"),
    "hydrogen": ("hydrogen", "h2"),
}
MAX_FILE_BYTES = 64 * 1024


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def _no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON field: " + key)
        obj[key] = value
    return obj


def _read_ontology(path: Path = ONTOLOGY) -> dict[str, Any]:
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_FILE_BYTES,
             "ontology missing, oversized or symlinked")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def validate_graph(graph: Any, *, source_record=None) -> dict:
    """Strict local graph and fixture consistency; NOT RDF/OWL inference."""
    if type(graph) is not dict or set(graph) != {
        "schema_version", "domain", "publication_id", "issued_to", "publication_date",
        "source_provenance", "evidence_kind", "patent_rights", "integration_targets",
        "peace_impact_transfer", "policy", "nodes", "edges"
    }:
        raise ValueError("ontology schema differs from version 1")
    _require(graph["schema_version"] == "1.0.0" and graph["publication_id"] == PATENT_ID
             and graph["issued_to"] == OWNER and graph["publication_date"] == "2026-10-13",
             "patent identity/third-party rights mismatch")
    _require(graph["source_provenance"] == PROVENANCE, "false official source verification")
    _require(graph["evidence_kind"] == "THIRD_PARTY_PATENT_DISCLOSURE_NOT_OPERATIONAL_VALIDATION" and
             graph["patent_rights"] == "THIRD_PARTY_RIGHTS_AND_FREEDOM_TO_OPERATE_REVIEW_REQUIRED" and
             graph["peace_impact_transfer"] == "NO_REAL_WORLD_PEACE_IMPACT_CAN_BE_INFERRED_FROM_PATENT_METADATA",
             "patent ownership, reality or peace trust boundary mismatch")
    integration = graph["integration_targets"]
    _require(type(integration) is list and len(integration) == 3 and
             integration == [
                 "integrations/gpt-doug-pineal/src/pineal/store.py",
                 "integrations/gpt-doug-pineal/src/pineal/patents.py",
                 "peace_impact/peacelab.ontology.jsonld"
             ], "integration links mismatch")
    policy = graph["policy"]
    _require(type(policy) is dict and set(policy) == {
        "physical_hardware_build_authorized", "dangerous_electrolysis_operations_authorized",
        "patent_license_or_ownership_granted", "independent_patent_or_claim_verification_completed",
        "clinical_or_biological_effect_proven", "humanitarian_impact_independently_verified",
        "external_network_or_chemical_actuation", "review_requirements"
    }, "unrecognized safety policy")
    _require(all(policy[key] is False for key in policy if key != "review_requirements"),
             "external physical or intellectual-property authorization cannot be granted")
    _require(policy["review_requirements"] == [
        "patent_counsel", "process_safety_engineer",
        "environmental_compliance_specialist", "independent_patent_source_verification"
    ], "human review role drift")
    nodes, edges = graph["nodes"], graph["edges"]
    _require(type(nodes) is list and len(nodes) == len(REQUIRED_NODES) and
             type(edges) is list and 12 <= len(edges) <= 32, "wrong size of ontology graph")
    seen, canonical_nodes = set(), []
    for item in nodes:
        _require(type(item) is dict and set(item) == {"id", "kind", "label"},
                 "unexpected graph node property")
        ident, kind, label = item["id"], item["kind"], item["label"]
        _require(type(ident) is str and ident in REQUIRED_NODES and ident not in seen,
                 "duplicate or unknown graph node")
        _require(type(kind) is str and kind in ALLOWED_KINDS and
                 type(label) is str and 1 <= len(label) <= 115 and
                 not any(ord(ch) < 32 or ord(ch) == 127 for ch in label),
                 "node label or class invalid")
        seen.add(ident)
        canonical_nodes.append(item)
    _require(seen == REQUIRED_NODES, "missing graph node")
    index = {node["id"]: node for node in canonical_nodes}
    _require(index["assignee"]["label"] == OWNER and
             index["hydrogen_gas"]["kind"] == "potential_coproduct" and
             index["chlorine_gas"]["kind"] == "potential_coproduct" and
             index["peace_truth"]["kind"] == "separate_boundary",
             "hazard/rights labels changed")
    seen_edges = set()
    for edge in edges:
        _require(type(edge) is dict and set(edge) == {"from", "to", "relation"},
                 "unrecognized edge fields")
        values = (edge["from"], edge["to"], edge["relation"])
        _require(all(type(v) is str for v in values) and
                 values[0] in seen and values[1] in seen and
                 values[2] in ALLOWED_RELATIONS and values not in seen_edges,
                 "duplicate, unrecognized or dangling graph edge")
        seen_edges.add(values)
    _require(REQUIRED_EDGES.issubset(seen_edges), "essential provenance/guardrail relations missing")
    record = _source_record() if source_record is None else source_record
    _require(record["publication_id"] == PATENT_ID and
             record["publication_date"] == graph["publication_date"] and
             record["title"].lower().startswith("methods and apparatuses for li extraction") and
             "user-provided" in record["source"].lower(),
             "sample metadata and ontology drift")
    return {
        "ontology_status": "VALID_LOCAL_SOURCE_GRAPH",
        "nodes": len(nodes), "links": len(edges),
        "record_source_type": "USER_SUPPLIED_UNVERIFIED",
        "third_party_rights_review_required": True,
        "physical_equipment_control_enabled": False,
        "remote_network_connected": False,
        "external_chemistry_verification": False,
        "peace_impact_proven": False,
        "ontology_sha256": _digest(graph),
        "sample_record_sha256": _digest(record),
        "audit_scope": "LOCAL_STRUCTURE_AND_PROVENANCE_NOT_EXTERNAL_TRUTH"
    }


def _source_record() -> dict:
    records = load_records(FIXTURE, limit=1)
    _require(len(records) == 1, "expected one user-supplied publication")
    return records[0]


def audit() -> dict:
    return validate_graph(_read_ontology())


def preview() -> dict:
    source = _source_record()
    return {
        "dry_run": True,
        "network_calls": 0,
        "database_writes": 0,
        "publication_id": source["publication_id"],
        "attributed_owner_from_user_excerpt": OWNER,
        "source": source["source"],
        "official_patent_grant_and_rights_independently_verified": False,
        "human_safety_and_patent_review_pending": True,
        "suggested_commit_command": "pineal nexus import-reference --commit",
        "note": "Only local bibliographic metadata. No manufacturing instructions."
    }


def import_reference(store: PinealStore, *, commit: bool = False) -> dict:
    if commit is not True:
        return preview()
    audit()
    source = _source_record()
    outcome = store.import_patents([source])
    return {
        "local_import": outcome, "network_calls": 0,
        "publication_id": PATENT_ID, "independent_legal_or_technical_verification": False,
        "third_party_rights": OWNER,
        "physical_process_executed": False,
        "existing_pineal_memory_index_updated": outcome["inserted"] == 1
    }


def _selected_index(store: PinealStore, record: dict) -> tuple[str, int]:
    # Existing PINEAL SQLite patent index, no external network.
    matches = [row for row in store.search_patents(PATENT_ID, limit=8)
               if row.get("publication_id") == PATENT_ID]
    if not matches:
        return "NOT_IMPORTED", 0
    fields = ("publication_id", "jurisdiction", "title", "publication_date", "abstract",
              "source", "source_url", "cpc", "cell_tags", "evidence_level")
    same = all(matches[0].get(k) == record.get(k) for k in fields)
    return ("USER_EXCERPT_METADATA_INDEXED" if same else
            "CONFLICTING_LOCAL_RECORD_REQUIRES_MANUAL_REVIEW"), len(matches)


def report(store: PinealStore) -> dict:
    graph = _read_ontology()
    graph_report = validate_graph(graph)
    source = _source_record()
    status, matches = _selected_index(store, source)
    stats = store.patent_stats()
    # This limited list is not an exhaustive patent landscape.
    sample = store.search_patents("", limit=20)
    clusters = {key: 0 for key in CLASSIFICATION_KEYWORDS}
    for row in sample:
        text = " ".join(str(row.get(key, "")) for key in ("title", "abstract", "cpc")).lower()
        for cluster, synonyms in CLASSIFICATION_KEYWORDS.items():
            if any(term in text for term in synonyms):
                clusters[cluster] += 1
    content = {
        "engine": "GPT_DOUG_BIOPINEAL_EVIDENCE_NEXUS_V1",
        "index_status": status,
        "publication_id": PATENT_ID,
        "claimed_assignee_in_user_excerpt": OWNER,
        "source_provenance": PROVENANCE,
        "official_uspto_record_verified": False,
        "grant_validity_and_freedom_to_operate_verified": False,
        "real_world_device_built_or_controlled": False,
        "sample_source_sha256": graph_report["sample_record_sha256"],
        "ontology_sha256": graph_report["ontology_sha256"],
        "local_metadata_matches": matches,
        "local_patent_metadata_total": stats["total"],
        "keyword_hits_within_last_20_local_records": clusters,
        "keyword_sample_size": len(sample),
        "cross_domain_peace_impact_verified": False,
        "independent_source_review_required": True,
        "patent_counsel_review_required": True,
        "hazard_reviews_required": ["hydrogen flammability", "chlorine toxicity",
                                    "lithium hydroxide caustic exposure"],
        "network_fetches": 0,
        "source_boundary": (
            "Metadata from a user-provided Patent Public Search excerpt; "
            "not independently verified official record, license, engineering outcome or safety assessment."
        ),
    }
    content["report_sha256"] = _digest(content)
    return content


def terminal_map(data: dict) -> str:
    """Compact, evidence-first actual local index visualization."""
    _require(data.get("engine") == "GPT_DOUG_BIOPINEAL_EVIDENCE_NEXUS_V1",
             "unexpected BioPineal report")
    lines = [
        "╔═══════════ GPT-DOUG / BIOPINEAL EVIDENCE NEXUS ═══════════╗",
        "║  LOCAL ONTOLOGY • THIRD-PARTY PATENT • ZERO PHYSICAL ACTUATION ║",
        "╚═══════════════════════════════════════════════════════════╝",
        "",
        "   [US 12,760,393 B1]  ── [PolyPlus Battery Company]",
        "                │         attribution from pasted excerpt",
        "           ┌────┴────────────┐",
        "           │                 │",
        "   [Brine/recycled feed]   [Li-ion membrane concept]",
        "           │                 │",
        "           └──────┬──────────┘",
        "                  │",
        "          [LiOH disclosure]  NOT VERIFIED",
        "           /        \\",
        "   [Potential H2] [Potential Cl2]",
        "      FLAMMABLE       TOXIC",
        "         └──── [HUMAN ENGINEERING / LEGAL REVIEW REQUIRED] ────",
        "",
        "  SQLITE STATUS: " + data["index_status"],
        "  LOCAL PATENT RECORDS: " + str(data["local_patent_metadata_total"]),
        "  SOURCE: USER-SUPPLIED / NOT INDEPENDENTLY VERIFIED",
        "  PATENT RIGHTS: THIRD PARTY / NO LICENSE OR OWNERSHIP",
        "  PEACE IMPACT: NONE VERIFIED FROM THIS PATENT",
        "  PROVIDER REQUESTS: 0  |  HARDWARE ACTIONS: 0",
        "  REPORT SHA-256: " + data["report_sha256"],
    ]
    return "\n".join(lines) + "\n"


def dot_graph() -> str:
    graph = _read_ontology()
    audit_report = validate_graph(graph)
    _require(audit_report["nodes"] == len(graph["nodes"]), "unexpected graph state")
    escape = lambda x: json.dumps(str(x), ensure_ascii=True)
    out = ['digraph BioPinealNexus {',
           '  graph [rankdir=LR, bgcolor="#07111f"];',
           '  node [shape=box, fontcolor="#eaf6ff", color="#314e64", '
           'style="rounded,filled", fillcolor="#132a3a"];',
           '  edge [color="#79d7ba"];']
    for node in graph["nodes"]:
        fill = {"hazard": "#682c41", "approval_required": "#655026",
                "verification_required": "#655026", "organization": "#264860"}.get(
                    node["kind"], "#132a3a")
        out.append("  " + escape(node["id"]) + " [label=" + escape(node["label"]) +
                   ", fillcolor=" + escape(fill) + "];")
    for edge in graph["edges"]:
        out.append("  " + escape(edge["from"]) + " -> " + escape(edge["to"]) +
                   " [label=" + escape(edge["relation"]) + "];")
    out.append("}")
    return "\n".join(out) + "\n"


def static_html(data: dict) -> str:
    """Generate local CSP-locked dashboard, HTML escaped, no JS and no network."""
    _require(data.get("engine") == "GPT_DOUG_BIOPINEAL_EVIDENCE_NEXUS_V1",
             "unexpected BioPineal report")
    escape = lambda s: html.escape(str(s), quote=True)
    graph = _read_ontology()
    validate_graph(graph)
    panels = [
        ("SOURCE", "User-supplied USPTO excerpt; official lookup not independently completed"),
        ("INDEX", data["index_status"]),
        ("ASSIGNEE", OWNER + " (attribution, not GPT-Doug ownership)"),
        ("DOCUMENT", PATENT_ID + " / publication claimed: 2026-10-13"),
        ("LOCAL RECORDS", str(data["local_patent_metadata_total"])),
        ("AUTONOMOUS ACTUATION", "NONE — local analysis only"),
    ]
    render_panels = "".join(
        "<article><h3>" + escape(k) + "</h3><p>" + escape(v) + "</p></article>"
        for k, v in panels
    )
    hazard_panels = "".join(
        "<article class='danger'><h3>" + escape(text) + "</h3><p>Qualified independent review required</p></article>"
        for text in data["hazard_reviews_required"]
    )
    counters = "".join(
        "<article><h3>" + escape(key).upper() + "</h3><p>" + escape(value) +
        " / limited local sample</p></article>"
        for key, value in data["keyword_hits_within_last_20_local_records"].items()
    )
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>GPT-Doug BioPineal | Lithium Evidence Nexus</title>
<style>:root{color-scheme:dark;font-family:system-ui,Arial;background:#07111f;color:#eaf6ff}
body{max-width:1150px;margin:auto;padding:30px 20px}header{border-bottom:1px solid #36536a;padding-bottom:25px}
h1{font-size:clamp(2rem,5vw,3.4rem);margin:10px 0}.tag{letter-spacing:.16em;color:#78e3d0;font-size:.75rem}
p{color:#c2d3df;line-height:1.5}.notice{padding:15px;border:1px solid #947544;border-radius:12px;background:#302820}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
article{padding:18px;border:1px solid #315068;border-radius:12px;background:#142a3c}
article h3{font-size:.84rem;color:#80dac3;letter-spacing:.06em}
.danger{background:#382632;border-color:#885b68}.danger h3{color:#ffbdbd}section{margin-top:32px}
small{font-size:.78rem}footer{margin-top:34px;border-top:1px solid #315068;padding-top:18px;overflow-wrap:anywhere}
</style></head><body><header><div class="tag">GPT-DOUG / BIOPINEAL / RESEARCH NEXUS</div>
<h1>Patent evidence / lithium–hydrogen</h1><p>Local ontology-first metadata and safety review.</p>
<div class="notice">THIRD-PARTY DISCLOSURE — NOT AN OPERATIONAL DEVICE, LICENSE OR VERIFIED PATENT RECORD</div>
</header><main><section><h2>Verified local system status</h2><div class="cards">""" +
render_panels + """</div></section><section><h2>Hazards and mandatory reviews</h2>
<div class="cards">""" + hazard_panels +
"""</div></section><section><h2>Keyword counts in locally indexed patent metadata</h2>
<p>Counts are lexical matches across at most 20 locally stored publications, not patents verified or scientifically evaluated.</p>
<div class="cards">""" + counters +
"""</div></section><section><h2>Rights and humanitarian boundary</h2><p>PolyPlus Battery Company is the assignee reported in the user-provided excerpt. No IP rights have transferred; legal, technical, and environmental reviews remain outstanding. This metadata alone is not evidence of verified peace impact.</p></section></main><footer>
<small>Offline report SHA-256: """ + escape(data["report_sha256"]) +
""" · no live data fetch · no physical equipment control</small></footer></body></html>
""")


def watch(store: PinealStore, *, frames: int = 3, interval: float = 0.6) -> int:
    if type(frames) is not int or not 1 <= frames <= 120:
        raise ValueError("watch frames must be 1 to 120")
    if type(interval) not in (int, float) or not 0.2 <= interval <= 10:
        raise ValueError("watch interval must be 0.2 to 10 seconds")
    for idx in range(frames):
        if sys.stdout.isatty():
            sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write(terminal_map(report(store)) + "\n")
        sys.stdout.flush()
        if idx + 1 < frames:
            time.sleep(interval)
    return 0
