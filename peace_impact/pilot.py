"""Offline PeaceLab pilot plan, documentary gates, and independent review artifacts.

Paperwork is not verification, safety clearance, authority to begin fieldwork,
or evidence of humanitarian impact. All consequential decisions stay with humans.
"""
from __future__ import annotations

import html
import math
import re
from typing import Any
from .core import MIN_AGGREGATE, day_string, digest, https_url, string

VERSION = "1.0"
PILOT_ID_PATTERN = re.compile(r"[a-z][a-z0-9-]{3,49}\Z")
GATES = (
    ("legal_partner", "Accountable legal organization and director", "independent organization reviewer"),
    ("community_voice", "Voluntary community input and local legitimacy", "community advisory council"),
    ("conflict_sensitivity", "Independent conflict and do-no-harm review", "qualified safeguarding reviewer"),
    ("consent_privacy", "Informed consent, privacy and opt-out protocol", "independent privacy reviewer"),
    ("human_facilitator", "Qualified impartial human facilitator", "community partner"),
    ("evaluation_protocol", "Preregistered independent evaluation and harm measures", "independent evaluator"),
    ("incident_response", "Human incident escalation and stop procedure", "qualified safeguarding reviewer"),
    ("conflict_of_interest", "Funding and conflict-of-interest transparency", "independent organization reviewer"),
)
STATES = {"PENDING", "DOCUMENTED_UNVERIFIED", "BLOCKED"}
PHASES = (
    {"days": "01-30", "name": "Partner and community scoping", "deliverable": "Community-advised safety and legal review", "permission": "NO FIELD ACTIVITY"},
    {"days": "31-60", "name": "Safeguards and preregistration", "deliverable": "Consent, evaluator protocol, qualified facilitator", "permission": "NO FIELD ACTIVITY"},
    {"days": "61-75", "name": "Conditional voluntary pilot", "deliverable": "Human-facilitated session with safety stop", "permission": "EXTERNAL APPROVAL REQUIRED"},
    {"days": "76-90", "name": "Follow-up, independent audit", "deliverable": "Publish vetted null, positive or negative findings", "permission": "INDEPENDENT RELEASE REVIEW"},
)
RISKS = (
    {"id": "retaliation", "risk": "Participation may invite retaliation", "mitigation": "No identifying public records and voluntary safe exit", "stop_trigger": "Any credible retaliation risk"},
    {"id": "power_imbalance", "risk": "Participation could become coercive", "mitigation": "Independent community review and opt-out", "stop_trigger": "Consent is compromised"},
    {"id": "privacy", "risk": "Small cohorts and stories identify people", "mitigation": "Suppress small cohorts, avoid raw narratives and recordings", "stop_trigger": "Suspected identity disclosure"},
    {"id": "escalation", "risk": "Dialogue could escalate disputes", "mitigation": "Exclude high-risk settings and involve qualified professionals", "stop_trigger": "Threat or escalating dispute"},
    {"id": "evaluation_bias", "risk": "Pre-post data could be overclaimed as causal peace benefit", "mitigation": "Independent preregistration and limitations", "stop_trigger": "Misleading efficacy or Nobel claim"},
)
MEASUREMENT_KEYS = {"participants_aggregate", "baseline_aggregate", "post_aggregate", "followup_aggregate", "adverse_event_observed", "reporting_complete"}


def pilot_demo() -> dict[str, Any]:
    """Synthetic only. No actual partner, activity, participant or consent."""
    return {
        "version": VERSION, "as_of": "2026-10-13",
        "pilot_id": "gpt-doug-peacelab-90-day",
        "program": "GPT-Doug PeaceLab community-guided educational pilot",
        "synthetic": True,
        "gates": [{"id": gid, "state": "PENDING", "evidence_urls": [], "reviewed_on": None} for gid, _, _ in GATES],
        "measurements": {
            "participants_aggregate": None, "baseline_aggregate": None,
            "post_aggregate": None, "followup_aggregate": None,
            "adverse_event_observed": None, "reporting_complete": False,
        },
    }


def _finite_score(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 5:
        raise ValueError("invalid aggregate score: " + field)
    return float(value)


def validated_pilot(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"version", "as_of", "pilot_id", "program", "synthetic", "gates", "measurements"}:
        raise ValueError("pilot snapshot has missing or unrecognized fields")
    if value["version"] != VERSION:
        raise ValueError("unsupported pilot version")
    day = day_string(value["as_of"])
    pid = string(value["pilot_id"], "pilot_id", 50)
    if not PILOT_ID_PATTERN.fullmatch(pid):
        raise ValueError("invalid pilot id")
    program = string(value["program"], "program", 120)
    if type(value["synthetic"]) is not bool:
        raise ValueError("synthetic must be boolean")
    synthetic = value["synthetic"]
    gates = value["gates"]
    if type(gates) is not list or len(gates) != len(GATES):
        raise ValueError("all pilot gates required")
    clean_gates = []
    for item, (gid, _, _) in zip(gates, GATES):
        if type(item) is not dict or set(item) != {"id", "state", "evidence_urls", "reviewed_on"}:
            raise ValueError("invalid gate schema")
        if item["id"] != gid or type(item["state"]) is not str or item["state"] not in STATES:
            raise ValueError("gate order, id or state mismatch")
        links = item["evidence_urls"]
        if type(links) is not list or len(links) > 3:
            raise ValueError("invalid gate URLs")
        clean_urls = [https_url(url) for url in links]
        if len(set(clean_urls)) != len(clean_urls):
            raise ValueError("duplicate gate evidence URLs")
        review_date = item["reviewed_on"]
        if item["state"] == "DOCUMENTED_UNVERIFIED":
            if not clean_urls or review_date is None:
                raise ValueError("documented gate needs public evidence link and date")
            review_date = day_string(review_date)
            if review_date > day:
                raise ValueError("review date cannot exceed snapshot date")
        elif review_date is not None:
            raise ValueError("unreviewed gate must not claim a review date")
        clean_gates.append({"id": gid, "state": item["state"], "evidence_urls": clean_urls, "reviewed_on": review_date})
    m = value["measurements"]
    if type(m) is not dict or set(m) != MEASUREMENT_KEYS:
        raise ValueError("invalid measurement schema")
    count = m["participants_aggregate"]
    if count is not None and (type(count) is not int or not MIN_AGGREGATE <= count <= 1000000):
        raise ValueError("participant count must be omitted or aggregate >= 10")
    scores = {key: _finite_score(m[key], key) for key in ("baseline_aggregate", "post_aggregate", "followup_aggregate")}
    incident = m["adverse_event_observed"]
    if incident is not None and type(incident) is not bool:
        raise ValueError("adverse event must be unknown, yes or no")
    if type(m["reporting_complete"]) is not bool:
        raise ValueError("reporting_complete must be boolean")
    if synthetic and (count is not None or any(score is not None for score in scores.values()) or
                      incident is not None or m["reporting_complete"]):
        raise ValueError("synthetic pilot cannot report actual participant measurements")
    if count is None and any(score is not None for score in scores.values()):
        raise ValueError("aggregate scores require a disclosable cohort size")
    if m["reporting_complete"] and (count is None or any(score is None for score in scores.values()) or incident is None):
        raise ValueError("complete reporting requires all descriptive monitoring fields")
    return {
        "version": VERSION, "as_of": day, "pilot_id": pid, "program": program,
        "synthetic": synthetic, "gates": clean_gates,
        "measurements": {"participants_aggregate": count, **scores,
                         "adverse_event_observed": incident,
                         "reporting_complete": m["reporting_complete"]},
    }


def pilot_assess(snapshot: Any) -> dict[str, Any]:
    """Documentation completeness ONLY; never certify approvals or field outcomes."""
    safe = validated_pilot(snapshot)
    counts = {status: sum(item["state"] == status for item in safe["gates"]) for status in sorted(STATES)}
    outstanding = [spec[0] for spec, item in zip(GATES, safe["gates"]) if item["state"] != "DOCUMENTED_UNVERIFIED"]
    status = ("MISSING_FIELD_PREREQUISITES" if outstanding else
              "SELF_REPORTED_COMPLETE_REQUIRES_INDEPENDENT_REVIEW")
    if any(item["state"] == "BLOCKED" for item in safe["gates"]) or safe["measurements"]["adverse_event_observed"] is True:
        status = "STOP_AND_HUMAN_REVIEW"
    m = safe["measurements"]
    difference = (round(m["post_aggregate"] - m["baseline_aggregate"], 6)
                  if m["post_aggregate"] is not None and m["baseline_aggregate"] is not None else None)
    report = {
        "kind": "GPT_DOUG_PEACELAB_PILOT_DESIGN_REVIEW",
        "input": safe, "phases": [dict(phase) for phase in PHASES],
        "risk_register": [dict(risk) for risk in RISKS],
        "gate_states": counts, "missing_or_blocked": outstanding,
        "documentation_status": status,
        "descriptive_aggregate_change_self_reported": difference,
        "measurement_causality": "NO_CAUSAL_PEACE_EFFECT_ESTABLISHED",
        "verified_real_world_outcomes": 0,
        "external_truth_validation": "NOT_PERFORMED",
        "human_field_authorization": "NEVER_GRANTED_BY_SOFTWARE",
        "requires_independent_ethics_and_community_approval": True,
        "nobel": {"nomination_submitted": False, "nobel_affiliation": False,
                  "qualified_external_nominator_required": True},
        "review": {"submission_type": "ENGINEERING_DESIGN_AND_PILOT_PROTOCOL",
                   "requested_review_roles": ["community representative", "peace facilitator",
                                              "safeguarding specialist", "independent evaluator", "privacy reviewer"],
                   "execution": "NO_FIELD_PILOT_ACTIVATED"},
    }
    report["sha256"] = digest(report)
    return report


def pilot_verify(report: Any) -> bool:
    try:
        return type(report) is dict and report == pilot_assess(report["input"])
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def pilot_review_markdown(report: Any) -> str:
    if not pilot_verify(report):
        raise ValueError("invalid or altered pilot report")
    safe = report["input"]
    program = safe["program"].replace("\\", "\\\\").replace("[", "\\[").replace("*", "\\*").replace("<", "&lt;")
    phases = ["| Days " + p["days"] + " | " + p["name"] + " | " + p["permission"] + " |" for p in PHASES]
    gates = ["| " + gid + " | " + row["state"] + " | " + role + " | " + str(len(row["evidence_urls"])) + " (unchecked) |"
             for (gid, _, role), row in zip(GATES, safe["gates"])]
    return "\n".join([
        "# GPT-Doug PeaceLab — 90-day pilot: independent design review", "",
        "**REQUEST FOR TECHNICAL AND COMMUNITY REVIEW — NOT A FIELD PILOT APPROVAL**", "",
        "Program: " + program,
        "Snapshot: " + safe["as_of"], "Pilot reference: " + safe["pilot_id"],
        "Synthetic: " + str(safe["synthetic"]), "",
        "## Proposed public-interest intervention",
        "A small, voluntary, impartial, human-facilitated peace-education and dialogue pilot. "
        "Local practitioners and community members control participation and safety decisions. "
        "No automated mediation or demonstrated peace effect is claimed.", "",
        "## 90-day delivery plan", "| Window | Phase | Release condition |",
        "|---|---|---|", *phases, "",
        "## Independent sign-off gates (evidence not independently checked)",
        "| Gate | Self-reported state | Required reviewer | Links |",
        "|---|---|---|---:|", *gates, "",
        "Documentation status: **" + report["documentation_status"] + "**", "",
        "## Pilot ethics and measurement",
        "- Informed voluntary consent, free withdrawal, no profiling or raw stories in the software.",
        "- Aggregate baseline, immediate and follow-up responses; disclose harms and attrition.",
        "- Pre-post measurements do NOT prove causal peace effects.",
        "- Suppress cohorts below 10; suppression alone does not establish anonymity.",
        "- Any harm, blocked gate, coercion or threatened disclosure requires STOP and human review.", "",
        "## Decisions requested from independent human reviewers",
        "1. Are the setting, community mandate and legal operator genuine and suitable?",
        "2. Are the safeguarding and consent protections sufficient to avoid coercion or retaliation?",
        "3. Is the evaluator independent and the measurement approach preregistered and credible?",
        "4. Are negative findings, privacy and conflicts of interest handled appropriately?", "",
        "## Truth boundary",
        "**Verified real-world peace outcomes: 0.**",
        "**No actual pilot, partner endorsement, nomination, or Nobel affiliation established.**",
        "Local SHA-256 replay digest: " + report["sha256"] + " (integrity, not external attestation).", "",
    ])


def pilot_dashboard_html(report: Any) -> str:
    """Offline, static, no scripts, no remote assets; escapes displayed user input."""
    if not pilot_verify(report):
        raise ValueError("invalid or altered pilot report")
    snap = report["input"]
    name = html.escape(snap["program"], quote=True)
    state = html.escape(report["documentation_status"], quote=True)
    phases = "".join('<div class="phase"><b>Days '+p["days"]+'</b><span>'+html.escape(p["name"])+
                     '</span><small>'+html.escape(p["permission"])+'</small></div>' for p in PHASES)
    gates = "".join('<section class="gate"><h3>'+html.escape(title)+'</h3><p>'+html.escape(role)+
                    '</p><strong>'+html.escape(record["state"])+'</strong></section>'
                    for (_, title, role), record in zip(GATES, snap["gates"]))
    return ("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; object-src 'none'">
<title>GPT-Doug PeaceLab | Independent review</title><style>
:root{font-family:system-ui,-apple-system,sans-serif;color-scheme:dark;background:#070d19;color:#ecf1fd}
body{margin:auto;max-width:1180px;padding:36px 22px}
header{border-bottom:1px solid #35475f;padding-bottom:26px}
h1{font-size:clamp(2rem,5vw,3.5rem);margin:12px 0}
p{line-height:1.55;color:#b9cbdf}
.eyebrow{font-size:.8rem;letter-spacing:.17em;color:#8af0d1}
strong{color:#ffce8f}.status{display:inline-block;padding:10px 14px;background:#23364b;border:1px solid #6986a3;border-radius:9px}
.timeline,.gates{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:20px 0}
.phase,.gate{background:#101b2c;border:1px solid #304357;border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:10px}
.phase small{color:#f5ca89}.gate h3{font-size:1rem;margin:0}.gate p{margin:0}.gate strong{font-size:.82rem}
footer{border-top:1px solid #35475f;padding-top:26px;margin-top:38px;color:#b9cbdf}
</style></head><body><header><div class="eyebrow">GPT-DOUG / PEACELAB / SAFEGUARDS</div>
<h1>Peacebuilding pilot / 90-day design</h1><p>""" + name + """</p><div class="status">""" + state +
"""</div><p>Independent community review requested; no field deployment or nomination.</p></header>
<main><h2>90-day proposed timeline</h2><div class="timeline">""" + phases +
"""</div><h2>Eight safeguards for independent review</h2><div class="gates">""" + gates +
"""</div><h2>Measurement limitations</h2><p>Independent evaluators must consider selection bias, attrition, adverse outcomes and whether any effect can be attributed.</p><p>Participation is voluntary; there is no identifiable participant data, recording, automatic intervention or authorization in this report.</p></main>
<footer><p>REAL-WORLD PEACE OUTCOMES VERIFIED BY THIS TOOL: <strong>0</strong>. No field authority, endorsement, Nobel nomination or award.</p><small>Static local HTML; no scripts, external fonts or network.</small></footer></body></html>""")
