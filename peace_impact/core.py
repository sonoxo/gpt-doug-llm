"""GPT-Doug PeaceLab: offline, privacy-conscious impact evidence registry.

This checks documentation completeness, NOT whether outcomes are true. Links are
not fetched; a digest proves deterministic replay, not independent verification.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import date
from urllib.parse import urlsplit

VERSION = "1.0"
MAX_ACTIVITIES = 100
MIN_AGGREGATE = 10
KINDS = {"dialogue_workshop", "peace_education", "humanitarian_coordination", "open_peace_tool"}
STATUSES = {"planned", "completed", "cancelled"}
PROGRAM_FIELDS = {"name", "legal_name", "legal_verified", "mission", "consent_policy", "human_oversight", "nonpartisan", "privacy_policy", "conflict_sensitivity_reviewed", "eligible_nominator_identified"}
ACTIVITY_FIELDS = {"id", "kind", "status", "day", "synthetic", "participants_aggregate", "indicator", "baseline", "followup", "method", "consent", "harm_monitoring", "harm_incidents", "evidence_urls", "external_review_urls", "limitations"}
PII = re.compile(r"(?:[A-Z0-9_.+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b(?:\+?\d[\d\s().-]{7,}\d)\b)", re.I)
ACTIVITY_ID = re.compile(r"^[a-z][a-z0-9-]{2,39}$")


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def string(value, field, max_length=300, empty=False):
    if type(value) is not str or len(value) > max_length or (not empty and not value.strip()):
        raise ValueError("invalid " + field)
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or PII.search(value):
        raise ValueError("possible identifying data or control character in " + field)
    return value.strip()


def boolean(value, field):
    if type(value) is not bool:
        raise ValueError(field + " must be boolean")
    return value


def integer(value, field):
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= 10_000_000:
        raise ValueError("invalid " + field)
    return value


def number(value, field):
    if value is None:
        return None
    if type(value) not in (int, float) or not -100_000 <= value <= 100_000:
        raise ValueError("invalid " + field)
    return float(value)


def day_string(value):
    if type(value) is not str or len(value) != 10 or any(ord(c) < 32 for c in value):
        raise ValueError("invalid ISO date")
    text = value
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError()
    except ValueError:
        raise ValueError("invalid ISO date") from None
    return text


def https_url(value):
    value = string(value, "evidence URL", 500)
    if "\\" in value:
        raise ValueError("unsafe URL")
    u = urlsplit(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443):
        raise ValueError("only ordinary public HTTPS links are accepted")
    host = u.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("private hostname")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
            raise ValueError("invalid public evidence hostname") from None
    else:
        if not address.is_global:
            raise ValueError("nonpublic IP URL")
    return value


def urls(value, name):
    if not isinstance(value, list) or len(value) > 5:
        raise ValueError("invalid " + name + ": expected 0-5 URLs")
    links = [https_url(link) for link in value]
    if len(set(links)) != len(links):
        raise ValueError("duplicate evidence links")
    return links


def fields(value, required, name):
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(name + " has missing or undocumented fields")
    return value


def validated(snapshot):
    fields(snapshot, {"version", "as_of", "program", "activities"}, "snapshot")
    if snapshot["version"] != VERSION:
        raise ValueError("unsupported version")
    prog = fields(snapshot["program"], PROGRAM_FIELDS, "program")
    p = {"name": string(prog["name"], "name", 120),
         "legal_name": string(prog["legal_name"], "legal_name", 140, empty=True),
         "mission": string(prog["mission"], "mission", 600)}
    for key in PROGRAM_FIELDS - {"name", "legal_name", "mission"}:
        p[key] = boolean(prog[key], key)
    if p["legal_verified"] and not p["legal_name"]:
        raise ValueError("legal verification requires candidate legal name")
    activities = snapshot["activities"]
    if not isinstance(activities, list) or len(activities) > MAX_ACTIVITIES:
        raise ValueError("too many activities")
    cleaned, seen = [], set()
    for record in activities:
        a = fields(record, ACTIVITY_FIELDS, "activity")
        ident = string(a["id"], "activity id", 40)
        if not ACTIVITY_ID.fullmatch(ident) or ident in seen:
            raise ValueError("duplicate or invalid activity id")
        seen.add(ident)
        kind = string(a["kind"], "activity kind", 40)
        status = string(a["status"], "activity status", 15)
        if kind not in KINDS or status not in STATUSES:
            raise ValueError("unknown activity kind or status")
        safe = {"id": ident, "kind": kind, "status": status,
                "day": day_string(a["day"]), "synthetic": boolean(a["synthetic"], "synthetic"),
                "participants_aggregate": integer(a["participants_aggregate"], "participants_aggregate"),
                "indicator": string(a["indicator"], "indicator", 200),
                "baseline": number(a["baseline"], "baseline"),
                "followup": number(a["followup"], "followup"),
                "method": string(a["method"], "method", 300),
                "consent": boolean(a["consent"], "consent"),
                "harm_monitoring": boolean(a["harm_monitoring"], "harm_monitoring"),
                "harm_incidents": integer(a["harm_incidents"], "harm_incidents"),
                "evidence_urls": urls(a["evidence_urls"], "evidence_urls"),
                "external_review_urls": urls(a["external_review_urls"], "external_review_urls"),
                "limitations": string(a["limitations"], "limitations", 360)}
        if status != "completed" and (safe["participants_aggregate"] is not None or
                                       safe["evidence_urls"] or safe["external_review_urls"]):
            raise ValueError("uncompleted work cannot claim participants or evaluation evidence")
        if status == "completed" and not safe["synthetic"] and not (safe["consent"] and p["human_oversight"] and p["privacy_policy"]):
            raise ValueError("real completed activities require consent, oversight and privacy safeguards")
        if safe["participants_aggregate"] is not None and 0 < safe["participants_aggregate"] < MIN_AGGREGATE:
            raise ValueError("do not store identifying small-cohort counts; use null instead")
        cleaned.append(safe)
    return {"version": VERSION, "as_of": day_string(snapshot["as_of"]),
            "program": p, "activities": cleaned}


def assess(payload):
    """Machine-check documentation quality, never real-world truth."""
    safe = validated(payload)
    p, all_acts = safe["program"], safe["activities"]
    real = [a for a in all_acts if a["status"] == "completed" and not a["synthetic"]]
    referenced = [a for a in real if a["evidence_urls"]]
    externally_linked = [a for a in referenced if a["external_review_urls"]]
    evaluable = [a for a in externally_linked if a["baseline"] is not None and
                 a["followup"] is not None and a["harm_monitoring"] and
                 a["harm_incidents"] is not None and a["consent"]]
    shareable = [a for a in real if a["participants_aggregate"] is not None and
                 a["participants_aggregate"] >= MIN_AGGREGATE]
    conditions = (
        (p["legal_verified"], "prove that an active legally eligible candidate organization exists"),
        (all(p[k] for k in ("human_oversight", "consent_policy", "privacy_policy", "nonpartisan")),
         "implement privacy, consent, neutrality and human oversight"),
        (p["conflict_sensitivity_reviewed"], "obtain independent conflict sensitivity review"),
        (bool(referenced), "document a real completed activity and its primary evidence"),
        (bool(evaluable), "publish third-party evaluation with baseline, followup and harm reporting"),
        (p["eligible_nominator_identified"], "independently confirm a qualified willing nominator"),
    )
    missing = [label for ok, label in conditions if not ok]
    records = [{"id": a["id"], "status": a["status"], "synthetic": a["synthetic"],
                "sha256": digest(a),
                "primary_sources_provided_unchecked": bool(a["evidence_urls"]),
                "external_review_links_provided_unchecked": bool(a["external_review_urls"]),
                "public_participant_count_self_reported": a["participants_aggregate"] if a in shareable else None}
               for a in all_acts]
    result = {"name": "GPT-Doug PeaceLab", "classification": "DOCUMENTATION_ONLY_NOT_VERIFIED_IMPACT",
              "input": safe,
              "counts": {"activities": len(all_acts), "completed_real_activities_self_reported": len(real),
                         "evidence_linked": len(referenced), "external_review_linked": len(externally_linked),
                         "complete_evaluation_fields": len(evaluable),
                         "independently_verified_impact_by_software": 0,
                         "public_disclosure_safe_participants_self_reported": sum(a["participants_aggregate"] for a in shareable)},
              "records": records,
              "nobel": {"eligibility_status": "DOCUMENTS_READY_FOR_HUMAN_REVIEW" if not missing else "NOT_READY",
                        "missing": missing, "deadline_next_regular_cycle": "2027-01-31",
                        "self_nomination_valid": False, "eligible_independent_nominator_required": True,
                        "selection_or_affiliation_not_claimed": True},
              "boundary": "Evidence links are not opened; software does not certify truth, beneficiary safety, a Nobel nomination or Nobel affiliation."}
    result["evidence_sha256"] = digest(result)
    return result


def verify(report):
    try:
        return type(report) is dict and report == assess(report["input"])
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def demo():
    return {"version": VERSION, "as_of": "2026-10-13",
            "program": {"name": "GPT-Doug PeaceLab demonstration", "legal_name": "", "legal_verified": False,
                        "mission": "Support voluntary, neutral and human-facilitated dialogue, with measurable safeguards.",
                        "consent_policy": True, "human_oversight": True, "nonpartisan": True,
                        "privacy_policy": True, "conflict_sensitivity_reviewed": False,
                        "eligible_nominator_identified": False},
            "activities": [{"id": "dialogue-pilot-001", "kind": "dialogue_workshop", "status": "planned",
                            "day": "2026-10-13", "synthetic": True, "participants_aggregate": None,
                            "indicator": "Voluntary participant safety assessment",
                            "baseline": None, "followup": None,
                            "method": "Opt-in aggregate pre-post workshop evaluation, subject to independent study design",
                            "consent": False, "harm_monitoring": False, "harm_incidents": None,
                            "evidence_urls": [], "external_review_urls": [],
                            "limitations": "Only a fictional planning example; no workshop or affected person reached."}]}


def facilitator_kit():
    return """# GPT-Doug PeaceLab: 45-minute dialogue toolkit

**Educational template only. A trained human facilitator must lead all sessions.**

## First: consent, equity and safety
- Participation is voluntary. Anyone may leave or decline to speak.
- Do not expose participants to retaliation, coercion, surveillance or unwanted identification.
- Assess power imbalances and risks of physical or emotional harm *before* convening anyone.
- Do not enter names, contacts, personal stories, medical information or protected traits into this toolkit.
- High-risk conflict situations require qualified local professionals, not software-mediated intervention.

## Human-facilitated session
1. **0–5 min — Agreements.** No threats, no harassment, no forced disclosure, no recording without permission.
2. **5–15 min — Voluntary listening.** Share needs in general terms, without naming or targeting any individual.
3. **15–25 min — Reflection.** The facilitator summarizes perspectives neutrally and invites corrections.
4. **25–35 min — Shared interests.** Suggest only voluntary, safe, realistic steps.
5. **35–40 min — Harm assessment.** Ask what could backfire, who might be excluded, and what safeguards are needed.
6. **40–45 min — Close.** Participants choose whether any next step is appropriate; offer opt-in feedback.

## Evaluation and audit
- Measure meaningful outcomes *and harms* with an approved independent evaluator.
- Publish methods and limitations, not identifying case files.
- Suppress participant counts from public reports for groups under 10; this alone is not anonymization.
- Do not call a workshop a peace outcome merely because it was held.

**Standards consulted:** UNESCO Recommendation on the Ethics of AI, ICRC Handbook on Data Protection in Humanitarian Action, UNDP Conflict Sensitivity Indicators. No partnership or endorsement implied.
"""


def review_brief(report):
    if not verify(report):
        raise ValueError("invalid impact report")
    return ("# Peace impact review brief\n\n"
            "**UNSUBMITTED DRAFT — NOT A NOBEL NOMINATION OR ENDORSEMENT**\n\n"
            "Programme: " + report["input"]["program"]["name"] + "\n\n"
            "Mission: " + report["input"]["program"]["mission"] + "\n\n"
            "Real completed initiatives (SELF-REPORTED): " + str(report["counts"]["completed_real_activities_self_reported"]) + "\n"
            "Independently verified peace outcomes: NONE (not evaluated by this software).\n\n"
            "## Missing evidence\n" + "".join("- " + x + "\n" for x in report["nobel"]["missing"])
            + "\nA qualified external nominator must nominate a living person or active organization by the deadline. "
              "This software cannot nominate itself, prove peace impact or guarantee an award.\n")
