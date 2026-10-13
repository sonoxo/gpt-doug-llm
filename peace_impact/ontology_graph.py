"""Read-only PeaceLab JSON-LD ontology, drift checks and terminal visualization.

The JSON-LD graph is RDF-ready, but this stdlib validator is NOT a full
JSON-LD 1.1 expansion processor, SHACL implementation or OWL reasoner.
Only exact local repository schemas and deny-first truth boundaries are tested.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from .core import digest
from .pilot import GATES, PHASES, RISKS

ROOT = Path(__file__).resolve().parent
ONTOLOGY = ROOT / "peacelab.ontology.jsonld"
LEGACY = ROOT / "ontology.json"
MAX_BYTES = 128 * 1024
NAMESPACE = "https://github.com/sonoxo/gpt-doug-llm/blob/main/peace_impact/peacelab.ontology.jsonld#"

CONTEXT = {
    "pl": NAMESPACE,
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    **{name: {"@id": "pl:" + name, "@type": "@id"} for name in
       ("hasPilot", "hasGate", "hasPhase", "hasRisk", "requiresHumanRole", "nextPhase", "hasTrustState")},
}
CLASSES = {
    "PeaceProgram": "prov:Entity",
    "PilotPlan": "prov:Plan",
    "SafetyGate": "prov:Entity",
    "HumanRole": "prov:Role",
    "PilotPhase": "prov:Activity",
    "Risk": "prov:Entity",
    "EvidenceRecord": "prov:Entity",
    "EvaluationMeasurement": "prov:Entity",
    "ReviewDecision": "prov:Entity",
    "SoftwareComponent": "prov:SoftwareAgent",
    "GovernancePolicy": "prov:Entity",
}
OBJECT_PROPERTIES = {
    "hasPilot": ("PeaceProgram", "PilotPlan"),
    "hasGate": ("PilotPlan", "SafetyGate"),
    "hasPhase": ("PilotPlan", "PilotPhase"),
    "hasRisk": ("PilotPlan", "Risk"),
    "requiresHumanRole": ("SafetyGate", "HumanRole"),
    "nextPhase": ("PilotPhase", "PilotPhase"),
    "hasTrustState": ("PilotPlan", "skos:Concept"),
}
ROLE_LABELS = {
    "independent-organization-reviewer": "Independent organization reviewer",
    "community-advisory-council": "Community advisory council",
    "qualified-safeguarding-reviewer": "Qualified safeguarding reviewer",
    "independent-privacy-reviewer": "Independent privacy reviewer",
    "community-partner": "Community partner",
    "independent-evaluator": "Independent evaluator",
    "qualified-human-facilitator": "Qualified human facilitator",
}
TRUST_LABELS = {
    "SYNTHETIC": "Synthetic model; no real person or outcome",
    "SELF_REPORTED": "Self-reported and not independently checked",
    "LINKS_PROVIDED_UNCHECKED": "Evidence URLs supplied; their truth is unchecked",
    "EXTERNAL_REVIEW_REQUIRED": "Independent assessment is still required",
}
DENY_POLICIES = {
    "no-automated-fieldwork": "Software never grants authority for external fieldwork",
    "no-autonomous-mediation": "No automated conflict mediation or intervention",
    "no-identity-tracking": "Do not store participant identities, biographies or raw stories",
    "no-unverified-impact": "Never equate hash/links, workshop counts or before-after differences with verified peace outcomes",
    "no-nobel-application": "Do not self-nominate or claim Nobel endorsement or award",
}
GATE_TO_ROLE = {
    "independent organization reviewer": "independent-organization-reviewer",
    "community advisory council": "community-advisory-council",
    "qualified safeguarding reviewer": "qualified-safeguarding-reviewer",
    "independent privacy reviewer": "independent-privacy-reviewer",
    "community partner": "community-partner",
    "independent evaluator": "independent-evaluator",
}
ROOT_FIELDS = {"@context", "@id", "@type", "rdfs:label", "rdfs:comment",
               "owl:versionInfo", "pl:ontologyStatus", "pl:authorityBoundary",
               "pl:verifiedRealWorldOutcomes", "pl:nobelNominationSubmitted", "@graph"}
GRAPH_REF_KEYS = ("hasPilot", "hasGate", "hasPhase", "hasRisk",
                  "requiresHumanRole", "nextPhase", "hasTrustState")
NODE_ID = re.compile(r"pl:[A-Za-z][A-Za-z0-9_-]*\Z")


def _fields(obj, names, title):
    if type(obj) is not dict or set(obj) != set(names):
        raise ValueError(title + ": unsupported, missing or extra fields")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _no_duplicate_keys(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError("duplicate JSON key: " + k)
        result[k] = v
    return result


def _local_file(path):
    p = Path(path)
    _require(not p.is_symlink() and p.is_file() and p.stat().st_size <= MAX_BYTES,
             "missing, symlinked, or oversized ontology file")
    return json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)


def load_ontology(path=None):
    """Load an authored graph. A user-supplied path is read only, never fetched."""
    return _local_file(ONTOLOGY if path is None else path)


def _node(nodes, ident, type_name, properties):
    full = "pl:" + ident
    _require(full in nodes, "missing ontology node " + full)
    item = nodes[full]
    _fields(item, {"@id", "@type", "rdfs:label"} | set(properties), full)
    _require(item["@type"] == type_name and type(item["rdfs:label"]) is str
             and bool(item["rdfs:label"].strip()) and len(item["rdfs:label"]) <= 260,
             "invalid type or label: " + full)
    for key, expected in properties.items():
        _require(item[key] == expected and type(item[key]) is type(expected),
                 "inconsistent ontology property " + full + "." + key)
    return item


def _typed_root(graph):
    _fields(graph, ROOT_FIELDS, "JSON-LD document")
    _require(graph["@context"] == CONTEXT, "unrecognized or remote JSON-LD context")
    _require(graph["@id"] == "pl:ontology" and graph["@type"] == "owl:Ontology",
             "invalid ontology root")
    _require(graph["owl:versionInfo"] == "1.0.0" and
             graph["pl:ontologyStatus"] == "ENGINEERING_REVIEW_ONLY" and
             graph["pl:authorityBoundary"] == "NEVER_GRANTED_BY_SOFTWARE",
             "ontology may not grant field authority")
    _require(type(graph["pl:verifiedRealWorldOutcomes"]) is int and
             graph["pl:verifiedRealWorldOutcomes"] == 0 and
             graph["pl:nobelNominationSubmitted"] is False,
             "no real-world peace or Nobel impact is verified")
    for key in ("rdfs:label", "rdfs:comment"):
        _require(type(graph[key]) is str and bool(graph[key].strip()),
                 "invalid root description")


def _expected_ids():
    return (
        {"pl:" + key for key in CLASSES} |
        {"pl:" + key for key in OBJECT_PROPERTIES} |
        {"pl:program", "pl:pilot-90-day", "pl:peacelab-software"} |
        {"pl:role-" + role for role in ROLE_LABELS} |
        {"pl:gate-" + row[0] for row in GATES} |
        {"pl:phase-" + row["days"] for row in PHASES} |
        {"pl:risk-" + row["id"] for row in RISKS} |
        {"pl:trust-" + t for t in TRUST_LABELS} |
        {"pl:policy-" + k for k in DENY_POLICIES}
    )


def _validate_legacy(legacy):
    _require(type(legacy) is dict, "missing legacy control policy")
    for field in ("automatic_external_impact_verification", "automatic_nobel_nomination",
                  "autonomous_conflict_intervention", "biometric_or_participant_tracking",
                  "surveillance"):
        _require(legacy.get(field) is False, "legacy safety policy drift: " + field)
    _require(legacy.get("human_oversight") is True, "human oversight is mandatory")
    _require(type(legacy.get("independently_verified_real_world_outcomes")) is int and
             legacy.get("independently_verified_real_world_outcomes") == 0,
             "legacy policy cannot claim real-world outcomes")
    _require(legacy.get("trust_states") == list(TRUST_LABELS),
             "legacy provenance state drift")


def audit_ontology(graph, *, legacy=None):
    """Strict, closed local audit; fail closed if pilot definitions drift."""
    _typed_root(graph)
    rows = graph["@graph"]
    _require(type(rows) is list and len(rows) <= 96, "invalid or oversized graph")
    nodes = {}
    for node in rows:
        _require(type(node) is dict and type(node.get("@id")) is str and
                 bool(NODE_ID.fullmatch(node["@id"])), "invalid graph node identifier")
        _require(node["@id"] not in nodes, "duplicate graph node " + node["@id"])
        nodes[node["@id"]] = node
    _require(set(nodes) == _expected_ids(), "ontology missing/extra nodes or pilot drift")
    # Classes and object-property IRIs are explicit and grounded.
    for name, supertype in CLASSES.items():
        _node(nodes, name, "owl:Class", {"rdfs:subClassOf": {"@id": supertype}})
    for name, (domain, range_id) in OBJECT_PROPERTIES.items():
        rng = range_id if ":" in range_id else "pl:" + range_id
        _node(nodes, name, "owl:ObjectProperty", {
            "rdfs:domain": {"@id": "pl:" + domain},
            "rdfs:range": {"@id": rng},
        })
    _node(nodes, "program", "pl:PeaceProgram", {
        "hasPilot": "pl:pilot-90-day", "pl:verifiedRealWorldOutcomes": 0,
        "pl:humanFieldAuthority": "NEVER_GRANTED_BY_SOFTWARE",
        "pl:nobelNominationSubmitted": False,
    })
    _node(nodes, "pilot-90-day", "pl:PilotPlan", {
        "hasTrustState": "pl:trust-SYNTHETIC",
        "hasGate": ["pl:gate-" + g[0] for g in GATES],
        "hasPhase": ["pl:phase-" + phase["days"] for phase in PHASES],
        "hasRisk": ["pl:risk-" + risk["id"] for risk in RISKS],
        "pl:executionStatus": "NO_FIELD_PILOT_ACTIVATED",
        "pl:externalApprovalGranted": False,
    })
    _node(nodes, "peacelab-software", "pl:SoftwareComponent", {
        "rdfs:comment": "Offline evidence verifier. It is not a human reviewer and cannot grant authority.",
    })
    for role, label in ROLE_LABELS.items():
        item = _node(nodes, "role-" + role, "pl:HumanRole", {
            "pl:identifiedOrApproved": False,
            "rdfs:comment": "Required function only; no real individual has been assigned.",
        })
        _require(item["rdfs:label"] == label, "human role label drift")
    for key, title, human_role in GATES:
        _require(human_role in GATE_TO_ROLE, "new pilot role requires ontological mapping")
        item = _node(nodes, "gate-" + key, "pl:SafetyGate", {
            "pl:gateKey": key,
            "pl:reviewState": "PENDING",
            "requiresHumanRole": "pl:role-" + GATE_TO_ROLE[human_role],
            "pl:externalAttestation": "NOT_PERFORMED",
        })
        _require(item["rdfs:label"] == title, "safety gate label drift: " + key)
    for idx, phase in enumerate(PHASES):
        nxt = ({"nextPhase": "pl:phase-" + PHASES[idx+1]["days"]}
               if idx + 1 < len(PHASES) else {})
        item = _node(nodes, "phase-" + phase["days"], "pl:PilotPhase", {
            "pl:days": phase["days"], "pl:permissionBoundary": phase["permission"], **nxt,
        })
        _require(item["rdfs:label"] == phase["name"], "phase label drift")
    for risk in RISKS:
        item = _node(nodes, "risk-" + risk["id"], "pl:Risk", {
            "pl:riskKey": risk["id"],
            "pl:mitigation": risk["mitigation"],
            "pl:stopTrigger": risk["stop_trigger"],
        })
        _require(item["rdfs:label"] == risk["risk"], "risk label drift")
    for state, label in TRUST_LABELS.items():
        item = _node(nodes, "trust-" + state, "skos:Concept", {"pl:trustCode": state})
        _require(item["rdfs:label"] == label, "trust state label drift")
    for key, text in DENY_POLICIES.items():
        item = _node(nodes, "policy-" + key, "pl:GovernancePolicy", {
            "pl:effect": "DENY", "pl:overrideBySoftware": False
        })
        _require(item["rdfs:label"] == text, "policy label drift")
    for item in rows:
        for field in GRAPH_REF_KEYS:
            if field not in item:
                continue
            targets = item[field] if type(item[field]) is list else [item[field]]
            _require(bool(targets), "empty typed relation " + field)
            for target in targets:
                _require(type(target) is str and target in nodes,
                         "unresolved graph reference: " + str(target))
    _validate_legacy(_local_file(LEGACY) if legacy is None else legacy)
    result = {
        "status": "VALID_REPOSITORY_ONTOLOGY", "graph_nodes": len(nodes),
        "classes": len(CLASSES), "relations": len(OBJECT_PROPERTIES),
        "human_roles_unassigned": len(ROLE_LABELS), "safety_gates_pending": len(GATES),
        "phases": len(PHASES), "harm_risks": len(RISKS),
        "provenance_states": len(TRUST_LABELS), "deny_policies": len(DENY_POLICIES),
        "ontology_sha256": digest(graph),
        "fieldwork_authorized": False,
        "external_peace_impact_verified": False,
        "nobel_nomination_submitted": False,
        "rdf_semantic_reasoning_performed": False,
        "note": "Local structural and project drift audit only; no independent external attestation."
    }
    return result


def text_map(graph):
    report = audit_ontology(graph)
    lines = [
        "╔════════ GPT-DOUG / PEACELAB ONTOLOGY ════════╗",
        "║  W3C JSON-LD graph  ·  " + str(report["graph_nodes"]) + " nodes  ·  REVIEW ONLY   ║",
        "╚═════════════════════════════════════════════╝",
        "",
        "[PeaceProgram: GPT-Doug PeaceLab]",
        "   │",
        "   └── [PilotPlan: 90 days]  STATUS: NOT RUNNING",
        "          ├── [Human roles] " + str(len(ROLE_LABELS)) + " placeholders (none appointed)",
        "          ├── [Safety gates] " + str(len(GATES)) + " PENDING",
    ]
    lines += ["          │     ├── " + key + " → " + role
              for key, _, role in GATES]
    lines += ["          ├── [Phases] 4 conditional stages"]
    lines += ["          │     ├── days " + p["days"] + ": " + p["permission"] for p in PHASES]
    lines += ["          ├── [Risks] " + str(len(RISKS)) + " potential harms"]
    lines += ["          │     ├── " + r["id"] for r in RISKS]
    lines += ["          └── [Policies] " + str(len(DENY_POLICIES)) + " DENY rules"]
    lines += ["                └── NEVER grants field authority / verifies peace impact",
              "", "PROVENANCE: SYNTHETIC → SELF_REPORTED → LINKS_UNCHECKED",
              "            ↳ Independent human verification required",
              "NO LIVE PARTICIPANTS · NO NOBEL NOMINATION · NO GLOBAL ACCESS",
              "LOCAL SHA-256: " + report["ontology_sha256"]]
    return "\n".join(lines) + "\n"


def graphviz_dot(graph):
    """Offline Graphviz DOT. Rendering to SVG is optional and user-controlled."""
    audit_ontology(graph)
    q = lambda text: json.dumps(str(text), ensure_ascii=True)
    lines = [
        "digraph GPTDougPeaceLab {", '  graph [rankdir=LR, bgcolor="#071320", pad="0.4"];',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", color="#24455D", fontcolor="#F2F7FF", fillcolor="#102538"];',
        '  edge [color="#67C2BD", arrowsize=0.65];',
    ]
    def n(ident, label, fill):
        lines.append("  " + q(ident) + " [label=" + q(label) + ", fillcolor=" + q(fill) + "];")
    def e(src, dst):
        lines.append("  " + q(src) + " -> " + q(dst) + ";")
    n("program", "PeaceLab", "#214F64")
    n("pilot", "90-day pilot\nNOT RUNNING", "#245263")
    e("program", "pilot")
    for key, title, role in GATES:
        n("gate-"+key, "GATE: "+key+"\nPENDING", "#665128")
        e("pilot", "gate-"+key)
        n("role-"+role, "HUMAN ROLE\n"+role, "#214235")
        e("gate-"+key, "role-"+role)
    for idx, phase in enumerate(PHASES):
        pid="phase-"+phase["days"]
        n(pid, "Days "+phase["days"]+"\n"+phase["permission"], "#244460")
        if idx==0:e("pilot",pid)
        else:e("phase-"+PHASES[idx-1]["days"],pid)
    for risk in RISKS:
        n("risk-"+risk["id"], "RISK: "+risk["id"], "#6B303F")
        e("pilot", "risk-"+risk["id"])
    for key in DENY_POLICIES:
        n("policy-"+key, "DENY: "+key, "#622D42")
        e("program", "policy-"+key)
    lines.append("}")
    return "\n".join(lines)+"\n"


def standalone_html(graph):
    """Static local HTML; no JS, external resources or permission controls."""
    report = audit_ontology(graph)
    esc = lambda s: html.escape(str(s), quote=True)
    section = lambda title, entries: ("<section><h2>" + esc(title) + "</h2><div class='cards'>" +
        "".join("<article><strong>"+esc(name)+"</strong><span>"+esc(description)+"</span></article>"
                for name, description in entries) + "</div></section>")
    gate_entries = [(key, "PENDING · requires " + role) for key, _, role in GATES]
    phase_entries = [("Days "+p["days"], p["name"]+" · "+p["permission"]) for p in PHASES]
    risk_entries = [(r["id"],r["stop_trigger"]) for r in RISKS]
    deny_entries = [(key, val) for key,val in DENY_POLICIES.items()]
    trust_entries = list(TRUST_LABELS.items())
    body = "".join([section("Safety gates — all unapproved",gate_entries),
                    section("90-day pilot phases",phase_entries),
                    section("Risk/stop triggers",risk_entries),
                    section("Deny-first policies",deny_entries),
                    section("Provenance and evidence states",trust_entries)])
    return ("""<!doctype html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>GPT-Doug PeaceLab Ontology Map</title>
<style>:root{color-scheme:dark;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:#071320;color:#f2f7ff}
body{max-width:1150px;margin:auto;padding:40px 24px}header{padding:26px 0;border-bottom:1px solid #335a6b}
h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.1;margin:15px 0}p{color:#a9c6d2;line-height:1.6}
.tag{font-weight:700;color:#75e5d1;letter-spacing:.14em;font-size:.8rem}
.alert{border:1px solid #826c49;border-radius:12px;background:#332a20;color:#ffe1ae;padding:13px 18px}
h2{font-size:1.35rem;margin:33px 0 14px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px}
article{background:#102538;border:1px solid #305267;border-radius:13px;padding:18px;min-height:76px;display:flex;flex-direction:column;gap:9px}
article strong{font-size:.95rem;color:#f3f8ff}article span{font-size:.84rem;line-height:1.4;color:#a9cad5}
footer{border-top:1px solid #335a6b;margin-top:40px;padding-top:22px;font-size:.82rem}</style></head>
<body><header><div class="tag">GPT-DOUG-LLM // PEACELAB / ONTOLOGY</div><h1>Peace, evidence, and human oversight</h1>
<p>54 linked ontology nodes · 8 human safety gates · 5 explicit deny policies</p>
<div class="alert">DESIGN ONLY — NO PILOT AUTHORIZATION, VERIFIED PEACE OUTCOMES OR NOBEL NOMINATION</div></header>
<main>""" + body + """</main><footer>Static offline JSON-LD map. Repository structural audit: """ +
esc(report["status"]) + """ · SHA-256 """ + esc(report["ontology_sha256"]) +
""" · Semantic RDF/OWL entailment and real-world attestations are not performed.</footer></body></html>
""")
