"""GPT-Doug BioPineal: offline patent provenance + balanced-reaction evidence.

Purely informational desk research. No electrolysis control, chemical process
optimization, laboratory instructions, patent rights assessment or production.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from fractions import Fraction

SOURCE = {
    "document_id": "US 12760393 B1",
    "publication_date": "2026-10-13",
    "title": "Methods and apparatuses for Li extraction and generation of high purity lithium hydroxide",
    "inventors": ["Steven J. Visco", "Yevgeniy S. Nimon", "Bruce D. Katz"],
    "assignee": "PolyPlus Battery Company",
    "application_number": "18/149524",
    "filing_date": "2023-01-03",
    "cpc": ["C22B26/12", "C25B1/16", "C25B9/19", "C25B13/07"],
    "source_kind": "USER_SUPPLIED_PATENT_SEARCH_EXCERPT",
    "official_record_independently_verified": False,
    "invention_owned_by_gpt_doug": False,
    "patent_license_or_permission_granted": False,
}
# This is the balanced equation quoted in the supplied patent text, not an
# operational process recipe. Each species formula has a deterministic count.
EQUATION = {"LiCl": -2, "H2O": -2, "LiOH": 2, "H2": 1, "Cl2": 1}
ATOMS = {
    "LiCl": {"Li": 1, "Cl": 1},
    "H2O": {"H": 2, "O": 1},
    "LiOH": {"Li": 1, "O": 1, "H": 1},
    "H2": {"H": 2},
    "Cl2": {"Cl": 2},
}
HAZARD = {
    "H2": "flammable gas; explosion and ignition hazards",
    "Cl2": "highly toxic inhalation hazard; corrosive",
    "LiOH": "corrosive substance; exposure hazards",
}
MODULE_STATE = "DESK_RESEARCH_ONLY_NO_PHYSICAL_OPERATION"


def checked_balance(equation=EQUATION):
    if set(equation) != set(ATOMS):
        raise ValueError("unrecognized or omitted chemical species")
    if any(type(v) is not int or v == 0 for v in equation.values()):
        raise ValueError("all coefficients must be nonzero integers")
    totals = {}
    for species, coeff in equation.items():
        for symbol, number in ATOMS[species].items():
            totals[symbol] = totals.get(symbol, 0) + coeff * number
    if any(value != 0 for value in totals.values()):
        raise ValueError("element mass balance fails")
    if equation != EQUATION:
        raise ValueError("only the quoted canonical equation is supported")
    return dict(sorted(totals.items()))


def report():
    balance = checked_balance()
    result = {
        "module": "GPT-Doug BioPineal Patent Knowledge",
        "state": MODULE_STATE,
        "patent": copy.deepcopy(SOURCE),
        "quoted_reaction": "2 LiCl + 2 H2O -> 2 LiOH + H2 + Cl2",
        "stoichiometric_coefficients": EQUATION,
        "net_element_balance": balance,
        "equation_balanced": True,
        "hazard_disclosures": HAZARD,
        "claims": [
            {"claim": 1, "subject": "dry transfer Li extraction, ceramic membrane with laminated cation-exchange layer", "status": "CLAIM_TEXT_EXCERPT_ONLY"},
            {"claim": 7, "subject": "Li extraction plant with staged processing and membrane wall structure", "status": "CLAIM_TEXT_EXCERPT_ONLY"},
            {"claim": 10, "subject": "dry transfer Li electrolysis circuit", "status": "CLAIM_TEXT_EXCERPT_ONLY"},
        ],
        "verification_boundary": (
            "Derived only from the supplied public-search excerpt. Equation balance "
            "does not demonstrate engineering feasibility, conversion yield, environmental "
            "performance, freedom to operate, patent ownership, or permission to use technology."
        ),
        "physical_process_activated": False,
        "nobel_or_government_endorsement": False,
    }
    result["sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return result


def verify(value):
    return type(value) is dict and value == report()


def terminal():
    r = report()
    lines = [
        "GPT-DOUG // BIOPINEAL PATENT EVIDENCE",
        "=" * 54,
        "PUBLIC SEARCH EXCERPT (not independently authenticated)",
        SOURCE["document_id"] + " | " + SOURCE["publication_date"],
        SOURCE["title"],
        "",
        "LiCl + water ─── [electrochemical separation, patent concept] ──>",
        "                LiOH + H2 + Cl2",
        "2 LiCl + 2 H2O → 2 LiOH + H2 + Cl2",
        "CHECK: exact atom-balance " + json.dumps(r["net_element_balance"]),
        "",
        "HAZARDS: H2 flammable; Cl2 toxic; LiOH corrosive.",
        "OWNERSHIP: assignee stated as PolyPlus Battery Company.",
        "BOUNDARY: no device controller, deployment or production.",
        "DIGEST: " + r["sha256"],
    ]
    return "\n".join(lines)+"\n"


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline patent provenance and elemental balance")
    p.add_argument("action", nargs="?", choices=["show","report","verify"], default="show")
    p.add_argument("file", nargs="?")
    a = p.parse_args(argv)
    if a.action == "show":
        print(terminal(),end="")
    elif a.action == "report":
        print(json.dumps(report(),indent=2,sort_keys=True))
    else:
        if not a.file:
            p.error("verify requires a report path")
        with open(a.file, encoding="utf-8") as fh:
            value=json.load(fh)
        valid=verify(value)
        print(json.dumps({"integrity_verified":valid,"patent_record_independently_verified":False}))
        return 0 if valid else 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
