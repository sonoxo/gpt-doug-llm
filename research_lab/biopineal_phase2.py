"""BioPineal Phase II: offline evidence graph and non-operational flow accounting.

No apparatus specifications, runtime controls, kinetics, yield predictions,
electrolysis parameters, or patent licensing assertions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from fractions import Fraction
from .biopineal_patent import SOURCE, EQUATION, ATOMS, checked_balance, HAZARD

STATUS = "DESK_RESEARCH_ONLY"
SOURCE_ID = "source:user-excerpt:US12760393B1"
REACTION_ID = "reaction:quoted-lithium-balance"

def graph():
    """Create a deterministic provenance-aware scientific claim graph."""
    nodes = [
        {"id": SOURCE_ID, "kind": "source", "label": SOURCE["document_id"],
         "verification": "UNVERIFIED_USER_EXCERPT", "rights": "NOT_ESTABLISHED"},
        {"id": "claim:patent-identity", "kind": "claim",
         "label": SOURCE["title"], "verification": "UNVERIFIED_USER_EXCERPT"},
        {"id": "claim:assignee", "kind": "claim",
         "label": SOURCE["assignee"], "verification": "UNVERIFIED_USER_EXCERPT"},
        {"id": REACTION_ID, "kind": "reaction",
         "label": "2 LiCl + 2 H2O -> 2 LiOH + H2 + Cl2",
         "verification": "ATOM_BALANCE_ONLY"},
    ]
    edges = [
        {"from": SOURCE_ID, "to": "claim:patent-identity", "type": "SUPPORTS_AS_EXCERPT"},
        {"from": SOURCE_ID, "to": "claim:assignee", "type": "SUPPORTS_AS_EXCERPT"},
        {"from": SOURCE_ID, "to": REACTION_ID, "type": "QUOTES"},
    ]
    for species in sorted(ATOMS):
        node_id = "chemical:" + species
        nodes.append({"id": node_id, "kind": "species", "label": species,
                      "hazard": HAZARD.get(species, "No hazard classification in source")})
        edges.append({"from": REACTION_ID, "to": node_id,
                      "type": "CONSUMES" if EQUATION[species] < 0 else "PRODUCES",
                      "stoichiometric_magnitude": abs(EQUATION[species])})
    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["from"], e["to"]))
    return {"schema_version": 1, "state": STATUS, "nodes": nodes, "edges": edges,
            "official_record_verified": False, "technology_use_rights_verified": False,
            "hardware_connected": False}

def validate_graph(value):
    if type(value) is not dict or value != graph():
        return False
    ids = [n["id"] for n in value["nodes"]]
    return len(ids) == len(set(ids)) and all(
        e["from"] in ids and e["to"] in ids for e in value["edges"])

def flow(units=1):
    """Conceptual balance in arbitrary equation units; not a process prediction."""
    if type(units) is not int or not 1 <= units <= 1000000:
        raise ValueError("units must be an integer from 1 to 1000000")
    balance = checked_balance()
    inputs = {k: -v * units for k, v in EQUATION.items() if v < 0}
    outputs = {k: v * units for k, v in EQUATION.items() if v > 0}
    return {"schema_version": 1, "state": STATUS, "unit": "ABSTRACT_STOICHIOMETRIC_UNITS",
            "input_coefficients": inputs, "output_coefficients": outputs,
            "element_residual": {k: v * units for k, v in balance.items()},
            "conversion_or_yield_predicted": False, "energy_estimated": False,
            "hazards": HAZARD, "physical_operation": False,
            "notice": "Equation bookkeeping only; not equipment, operating, or feasibility guidance."}

def report():
    value = {"graph": graph(), "flow": flow(),
             "source_notice": "Unverified user-supplied excerpt; no patent rights established."}
    value["sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
    return value

def verify(value):
    return type(value) is dict and value == report() and validate_graph(value["graph"])

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["graph", "flow", "report", "verify"], nargs="?", default="report")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--units", type=int, default=1)
    args = parser.parse_args(argv)
    if args.action == "verify":
        if not args.file: parser.error("verify requires a JSON file")
        with open(args.file, encoding="utf-8") as fh: data = json.load(fh)
        valid = verify(data)
        print(json.dumps({"integrity_verified": valid, "official_record_verified": False}))
        return 0 if valid else 1
    value = graph() if args.action == "graph" else flow(args.units) if args.action == "flow" else report()
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
