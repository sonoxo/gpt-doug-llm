"""GPT-Doug PeaceLab / Nobel Peace Prize 2027 evidence readiness review.

A *private, local* evidence inventory and reproducible engineering review report.
The Nobel Committee, not this software, decides winners and nomination validity.
No prize applications, external outreach, impact verification or fieldwork occur.
"""
from __future__ import annotations

import html
from datetime import date
from typing import Any

from .core import digest, https_url, string
from .pilot import pilot_assess, pilot_demo
from .ontology_graph import audit_ontology, load_ontology

VERSION = "1.0"
SNAPSHOT_DATE = "2026-10-13"
DEADLINE = "2027-01-31"
OFFICIAL_SOURCES = (
    "https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/",
    "https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/criteria-for-nominators",
    "https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/the-nomination-process",
    "https://www.nobelpeaceprize.org/laureates/2026",
    "https://www.nobelpeaceprize.org/nobel-peace-prize/nomination/confidentiality",
)
NOMINATOR_CATEGORIES = {
    "HEAD_OF_STATE_OR_GOVERNMENT_OR_NATIONAL_ASSEMBLY_MEMBER",
    "ICJ_OR_PCA_MEMBER",
    "INSTITUT_DE_DROIT_INTERNATIONAL_MEMBER",
    "WILPF_INTERNATIONAL_BOARD_MEMBER",
    "ELIGIBLE_UNIVERSITY_ACADEMIC_OR_RECTOR",
    "PEACE_RESEARCH_OR_FOREIGN_POLICY_INSTITUTE_DIRECTOR",
    "NOBEL_PEACE_PRIZE_LAUREATE",
    "NOBEL_PEACE_PRIZE_ORGANIZATION_BOARD_MEMBER",
    "NORWEGIAN_NOBEL_COMMITTEE_CURRENT_OR_FORMER_MEMBER",
    "FORMER_NOBEL_COMMITTEE_ADVISER",
}
CANDIDATE_KINDS = {"UNDETERMINED", "LIVING_INDIVIDUAL", "ACTIVE_ORGANIZATION"}
EVIDENCE_FIELDS = (
    "candidate_public_identity",
    "community_partner_review",
    "consent_and_safeguarding_review",
    "real_world_activities_report",
    "independent_outcome_evaluation",
    "unintended_harms_disclosure",
    "qualified_nominator_basis",
)
EVIDENCE_DESCRIPTIONS = {
    "candidate_public_identity": "Proof that a specific living person or active organization is the proposed candidate",
    "community_partner_review": "Independent local community buy-in and consent of responsible human partners",
    "consent_and_safeguarding_review": "Independent human privacy, consent and do-no-harm assessment",
    "real_world_activities_report": "Real completed actions with dates and verifiable public documentation",
    "independent_outcome_evaluation": "Independent rigorous assessment of peace outcomes, limitations and attribution",
    "unintended_harms_disclosure": "Documented consideration of adverse outcomes, coercion, retaliation and privacy risks",
    "qualified_nominator_basis": "Public basis for believing an independent proposed nominator fits an official category",
}
MIN_PUBLIC_COHORT = 10


def _fail_unless(condition: bool, error: str) -> None:
    if not condition:
        raise ValueError(error)


def template() -> dict[str, Any]:
    """Publishable synthetic template. Not a claim of a qualifying candidate."""
    return {
        "version": VERSION,
        "as_of": SNAPSHOT_DATE,
        "initiative": "GPT-Doug PeaceLab",
        "candidate_kind": "UNDETERMINED",
        "candidate_label": "GPT-Doug-LLM software project; individual or active organization not designated",
        "evidence_urls": {key: [] for key in EVIDENCE_FIELDS},
        "proposed_nominator_category": None,
        "nominator_submission_status": "NO_SUBMISSION_EVIDENCE_RECORDED",
        "completed_activities_self_reported": 0,
        "aggregate_participants_self_reported": None,
        "claims_are_synthetic": True,
    }


def validate_inventory(entry: Any) -> dict[str, Any]:
    """Strict structure. Evidence links are sanitized but never fetched/authenticated."""
    required = set(template())
    _fail_unless(type(entry) is dict and set(entry) == required,
                 "unexpected or missing Nobel readiness fields")
    _fail_unless(entry["version"] == VERSION, "unsupported inventory version")
    as_of = entry["as_of"]
    _fail_unless(type(as_of) is str and len(as_of) == 10 and date.fromisoformat(as_of).isoformat() == as_of,
                 "invalid date")
    _fail_unless(SNAPSHOT_DATE <= as_of <= DEADLINE,
                 "unsupported Nobel rules snapshot window; refresh official rules for a new award cycle")
    _fail_unless(entry["initiative"] == "GPT-Doug PeaceLab",
                 "initiative must match audited software")
    kind = entry["candidate_kind"]
    _fail_unless(type(kind) is str and kind in CANDIDATE_KINDS,
                 "candidate must be a living individual or active organization, not software")
    name = string(entry["candidate_label"], "candidate label", max_length=125)
    evidence = entry["evidence_urls"]
    _fail_unless(type(evidence) is dict and set(evidence) == set(EVIDENCE_FIELDS),
                 "unrecognized evidence types")
    clean = {}
    for key in EVIDENCE_FIELDS:
        vals = evidence[key]
        _fail_unless(type(vals) is list and len(vals) <= 3, "up to three public evidence URLs per field")
        values = [https_url(v) for v in vals]
        _fail_unless(len(set(values)) == len(values), "repeated evidence reference")
        clean[key] = values
    nominee_cat = entry["proposed_nominator_category"]
    _fail_unless(nominee_cat is None or (type(nominee_cat) is str and
                 nominee_cat in NOMINATOR_CATEGORIES),
                 "unsupported nominator category")
    submitted = entry["nominator_submission_status"]
    _fail_unless(type(submitted) is str and submitted in {
        "NO_SUBMISSION_EVIDENCE_RECORDED",
        "NOMINATOR_SELF_REPORT_ONLY",
    }, "invalid nomination status")
    count = entry["completed_activities_self_reported"]
    _fail_unless(type(count) is int and 0 <= count <= 100000,
                 "real-world activity count must be nonnegative integer")
    n = entry["aggregate_participants_self_reported"]
    _fail_unless(n is None or (type(n) is int and MIN_PUBLIC_COHORT <= n <= 10000000),
                 "participant cohorts below 10 or unsafe counts are not public")
    syn = entry["claims_are_synthetic"]
    _fail_unless(type(syn) is bool, "synthetic state must be boolean")
    if syn:
        _fail_unless(count == 0 and n is None and nominee_cat is None and
                     submitted == "NO_SUBMISSION_EVIDENCE_RECORDED" and
                     all(not urls for urls in clean.values()),
                     "synthetic sample cannot claim real evidence, results or nominator")
    if kind == "UNDETERMINED":
        _fail_unless(not clean["candidate_public_identity"],
                     "cannot provide validated identity under unspecified candidate")
    if submitted == "NOMINATOR_SELF_REPORT_ONLY":
        _fail_unless(nominee_cat is not None,
                     "nominator self-report requires a proposed qualified category")
    return {
        "version": VERSION, "as_of": as_of, "initiative": "GPT-Doug PeaceLab",
        "candidate_kind": kind, "candidate_label": name, "evidence_urls": clean,
        "proposed_nominator_category": nominee_cat,
        "nominator_submission_status": submitted,
        "completed_activities_self_reported": count,
        "aggregate_participants_self_reported": n,
        "claims_are_synthetic": syn,
    }


def review(entry: Any = None) -> dict[str, Any]:
    """Rechecks real repo policies, but never promotes metadata to true external impact."""
    inv = validate_inventory(template() if entry is None else entry)
    onto = audit_ontology(load_ontology())
    pilot = pilot_assess(pilot_demo())
    _fail_unless(onto["status"] == "VALID_REPOSITORY_ONTOLOGY" and
                 onto["fieldwork_authorized"] is False and
                 onto["external_peace_impact_verified"] is False and
                 pilot["verified_real_world_outcomes"] == 0,
                 "underlying ontology/pilot trust boundary changed")
    blockers = []
    if inv["candidate_kind"] == "UNDETERMINED" or not inv["evidence_urls"]["candidate_public_identity"]:
        blockers.append("Designate and independently verify one living individual or active organization")
    if not inv["evidence_urls"]["community_partner_review"]:
        blockers.append("Establish authentic community-led, human-approved peacebuilding partnership")
    if not inv["evidence_urls"]["consent_and_safeguarding_review"]:
        blockers.append("Complete independent human safeguarding, consent and privacy review")
    if (inv["completed_activities_self_reported"] == 0 or
            not inv["evidence_urls"]["real_world_activities_report"]):
        blockers.append("Complete real, documented and consented humanitarian or peacebuilding work")
    if not inv["evidence_urls"]["independent_outcome_evaluation"]:
        blockers.append("Obtain independent evaluation of benefits, confounders and negative results")
    if not inv["evidence_urls"]["unintended_harms_disclosure"]:
        blockers.append("Document harms, risks and limitations without personal participant data")
    if inv["proposed_nominator_category"] is None or not inv["evidence_urls"]["qualified_nominator_basis"]:
        blockers.append("Locate a willing, qualified, independent nominator and verify eligibility")
    if inv["nominator_submission_status"] == "NO_SUBMISSION_EVIDENCE_RECORDED":
        blockers.append("Only a qualified nominator may submit an authentic nomination before the deadline")
    else:
        blockers.append("Self-reported submission is not confirmation by the Nobel Institute; candidate validity unknown")
    report = {
        "version": VERSION, "status": "NOT_A_NOMINATION_OR_AWARD",
        "as_of": inv["as_of"], "candidate": {
            "kind_self_reported": inv["candidate_kind"],
            "label": inv["candidate_label"],
            "legal_or_personal_eligibility_independently_verified": False,
        },
        "official_rules": {
            "reference_date": SNAPSHOT_DATE,
            "next_regular_deadline": DEADLINE,
            "candidate_options": ["LIVING_INDIVIDUAL", "ACTIVE_ORGANIZATION"],
            "software_repository_alone_eligible": False,
            "self_application_valid": False,
            "qualified_external_nominator_required": True,
            "allowed_nominator_categories": sorted(NOMINATOR_CATEGORIES),
            "nobel_committee_exclusive_selection": True,
            "confidentiality_years": 50,
            "nomination_implies_nobel_endorsement": False,
            "2026_prize_already_awarded_to": "Navanethem (Navi) Pillay",
            "sources": list(OFFICIAL_SOURCES),
        },
        "project_evidence": {
            "completed_real_activities_self_reported": inv["completed_activities_self_reported"],
            "public_aggregate_participants_self_reported": inv["aggregate_participants_self_reported"],
            "public_evidence_links_unchecked": {key: len(vals) for key, vals in inv["evidence_urls"].items()},
            "proposed_nominator_category_self_reported": inv["proposed_nominator_category"],
            "nomination_submission_statement_unverified": inv["nominator_submission_status"],
            "local_ontology_consistency_check": onto["status"],
            "pending_gates_in_default_synthetic_pilot": pilot["gate_states"]["PENDING"],
            "pilot_example_is_synthetic": True,
            "independently_verified_impact_by_this_software": 0,
            "verified_human_reviewers_by_this_software": 0,
        },
        "formal_nomination_process": "INCOMPLETE_OR_NOT_AUTHENTICATED",
        "peace_impact_evidence": "NOT_INDEPENDENTLY_ESTABLISHED",
        "blockers": blockers,
        "independent_human_and_community_review_needed": True,
        "the_nobel_committee_alone_can_award": True,
        "actual_nobel_nomination_submitted_by_this_software": False,
        "actual_nobel_award_by_this_software": False,
        "limitations": (
            "Links and self-reporting are not fetched or authenticated; the example pilot is synthetic. "
            "Nominee eligibility, external nomination, and peace impact must be assessed by real humans. "
            "A complete dossier cannot compel an award."
        ),
        "input": inv,
    }
    report["sha256"] = digest(report)
    return report


def verify_report(report: Any) -> bool:
    """Integrity and deterministic replay only, NEVER official verification."""
    try:
        return type(report) is dict and review(report["input"]) == report
    except (ValueError, TypeError, OverflowError, KeyError, AttributeError):
        return False


def reviewer_brief(report: Any) -> str:
    if not verify_report(report):
        raise ValueError("tampered or unsupported report")
    fields = report["project_evidence"]["public_evidence_links_unchecked"]
    lines = [
        "# GPT-Doug PeaceLab — 2027 Nobel Peace Prize readiness audit",
        "", "**INTERNAL PREPARATION / NOT AN OFFICIAL NOMINATION OR NOBEL AFFILIATION**", "",
        "Report date: " + report["as_of"],
        "Candidate category (self-reported): " + report["candidate"]["kind_self_reported"],
        "Next nomination deadline: " + DEADLINE,
        "2026 prize: awarded to Navi Pillay; cannot be changed.", "",
        "## Evidence inventory (unverified links, NOT validated outcomes)",
        "| Evidence category | Number of URLs supplied |",
        "| --- | ---: |",
    ]
    lines.extend("| " + name + " | " + str(fields[name]) + " |" for name in EVIDENCE_FIELDS)
    lines += [
        "", "## Outstanding requirements and project-defined evidence gates",
    ]
    lines.extend("- " + b for b in report["blockers"])
    lines += [
        "", "## Next responsible actions",
        "1. Verify an active organization or living person as the proposed candidate; do not nominate a Git repository.",
        "2. Obtain genuine local community demand, consent and appropriate independent safeguarding review.",
        "3. Conduct only separately authorized human-led peacebuilding activities; evaluate benefits, null results and harms.",
        "4. Independently examine evidence and confirm legal/entity identity; do not manufacture endorsements.",
        "5. If real merit exists, let a qualified independent nominator submit voluntarily by 31 January 2027.",
        "6. Respect the Nobel Committee's confidentiality and exclusive decision-making.", "",
        "## Verification boundary",
        "**Observed independent peace impact confirmed by the software: 0.**",
        "**Actual Nobel nomination submitted by this software: NO.**",
        "**Nobel award: NO.**",
        "The Nobel Institute does not confirm nominee lists until 50 years have elapsed.",
        "Local SHA-256 integrity digest: " + report["sha256"],
        "Only integrity and local policy drift are checked; third-party truth is not authenticated.",
        "", "Official sources:",
    ]
    lines.extend("- " + url for url in OFFICIAL_SOURCES)
    return "\n".join(lines) + "\n"


def visual_html(report: Any) -> str:
    """Script-free, network-free reviewer dashboard."""
    if not verify_report(report):
        raise ValueError("invalid dossier certificate")
    esc = lambda value: html.escape(str(value), quote=True)
    cards = [
        ("2026 AWARD", "Already awarded to Navi Pillay"),
        ("2027 DEADLINE", DEADLINE),
        ("CANDIDATE", "Unverified; software itself ineligible"),
        ("NOMINATOR", "Independent qualified human required"),
        ("PEACE OUTCOMES", "0 independently verified by this tool"),
        ("NOMINATION", "Not submitted by this tool"),
    ]
    blocks = "".join(
        "<section><h3>" + esc(a) + "</h3><p>" + esc(b) + "</p></section>"
        for a,b in cards
    )
    missing = "".join("<li>"+esc(item)+"</li>" for item in report["blockers"])
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>GPT-Doug Nobel Peace Prize readiness audit</title>
<style>:root{font-family:system-ui,Arial;color-scheme:dark;background:#081222;color:#e8f3ff}
body{max-width:1050px;margin:auto;padding:35px 22px}.label{color:#91dac5;letter-spacing:.15em;font-size:.8rem}
header{border-bottom:1px solid #38506a;padding-bottom:24px}
h1{font-size:clamp(2rem,5vw,3.3rem)}.status{padding:12px;background:#302823;border:1px solid #8b673e;border-radius:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:25px 0}
section{background:#12283b;border:1px solid #37556b;border-radius:12px;padding:17px}
h3{font-size:.8rem;color:#9ddccc;letter-spacing:.12em}
p,li{line-height:1.55;color:#cbdce8}li{margin:8px 0}
footer{border-top:1px solid #38506a;margin-top:30px;padding:20px 0;font-size:.8rem}
</style></head><body><header><p class="label">GPT-DOUG-LLM // PEACELAB / 2027</p>
<h1>Nobel Peace Prize readiness</h1><div class="status"><strong>NOT AN AWARD OR SUBMITTED NOMINATION</strong></div>
<p>This local dashboard is an evidence audit, not a Nobel application or humanitarian endorsement.</p></header>
<main><div class="grid">""" + blocks +
"""</div><h2>Work that cannot be bypassed</h2><ol>""" + missing +
"""</ol><p>Only an eligible independent nominator can submit; only the Nobel Committee can choose the laureate. This report performs no verification of human identity or actual peace outcomes.</p></main>
<footer>Offline report / integrity SHA-256: """ + esc(report["sha256"]) +
""" · No network, tracking or participant data.</footer></body></html>""")
