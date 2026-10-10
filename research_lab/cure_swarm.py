"""Bio-Gpt Cure Swarm: bounded oncology evidence mapping, not a cure generator.

Public clinical-trial and literature metadata, human-reviewed research questions,
no diagnoses, drug dosing, wet-lab control, autonomous experiments or treatments.
Offline by default. --online explicitly fetches two known, public HTTPS APIs.
Python 3.9+ standard library, deterministic digest/replay for supplied snapshots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib import error, parse, request

VERSION = "bio-gpt-cure-swarm/v1"
MAX_QUERY = 72
MAX_RECORDS = 20
MAX_SOURCE_RESULTS = 10
MAX_INPUT_BYTES = 160_000
MAX_RESPONSE_BYTES = 750_000
API_TRIALS = "https://clinicaltrials.gov/api/v2/studies"
API_PAPERS = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
CANCER_QUERY = re.compile(r"[A-Za-z][A-Za-z0-9 -]{2,71}\Z")
NCT_ID = re.compile(r"NCT\d{8}\Z")
ARTICLE_ID = re.compile(r"(MED|PMC|PPR):[A-Za-z0-9.]{1,32}\Z")
SYN_ID = re.compile(r"SIM-(TRIAL|PAPER)-\d{1,5}\Z")
LIMITS = {"max_per_source": MAX_SOURCE_RESULTS, "max_records": MAX_RECORDS,
          "max_response_bytes": MAX_RESPONSE_BYTES, "max_query_chars": MAX_QUERY}
KINDS = {"trial", "paper"}
REQUIRED = {
    "trial": {"kind", "id", "title", "status", "phase", "study_type",
              "results_posted", "randomized", "updated", "source", "url"},
    "paper": {"kind", "id", "title", "publication_type", "retracted",
              "publication_date", "source", "url"},
}


def valid_query(value: Any) -> str:
    """A topic, never a patient name, patient notes or arbitrary query syntax."""
    if not isinstance(value, str) or not CANCER_QUERY.fullmatch(value.strip()):
        raise ValueError("query must be 3-72 alphanumeric cancer-topic characters")
    query = " ".join(value.strip().split())
    if len(query) > MAX_QUERY:
        raise ValueError("query too long")
    return query


def short_text(value: Any, max_length: int = 220) -> str:
    if not isinstance(value, str):
        return ""
    # Prevent control-character terminal injection and giant source strings.
    text = "".join(c if c.isprintable() else " " for c in value)
    return " ".join(text.split())[:max_length]


def _checked_str(value: Any, max_length: int = 220) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ValueError("invalid text field")
    if value != short_text(value, max_length):
        raise ValueError("untrusted formatting in text field")
    return value


def _canonical_record(raw: Any, origin: str) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
        raise ValueError("invalid record kind")
    kind = raw["kind"]
    if set(raw) != REQUIRED[kind]:
        raise ValueError("record contains missing or unsupported fields")
    out = dict(raw)
    record_id = _checked_str(out["id"], 50)
    if origin == "synthetic":
        if not SYN_ID.fullmatch(record_id):
            raise ValueError("synthetic records must use SIM- identifiers")
    elif kind == "trial":
        if not NCT_ID.fullmatch(record_id):
            raise ValueError("invalid ClinicalTrials.gov study ID")
    elif not ARTICLE_ID.fullmatch(record_id):
        raise ValueError("invalid Europe PMC publication ID")
    _checked_str(out["title"])
    if kind == "trial":
        for key in ("status", "phase", "study_type", "updated"):
            value = out[key]
            if not isinstance(value, str) or len(value) > 60 or value != short_text(value, 60):
                raise ValueError("invalid clinical trial metadata")
        for key in ("results_posted", "randomized"):
            if out[key] is not None and type(out[key]) is not bool:
                raise ValueError("trial evidence flags must be bool or unknown")
        expected = ("https://clinicaltrials.gov/study/" + record_id
                    if origin == "public_api" else None)
    else:
        for key in ("publication_type", "publication_date"):
            value = out[key]
            if not isinstance(value, str) or len(value) > 100 or value != short_text(value, 100):
                raise ValueError("invalid publication metadata")
        if out["retracted"] is not None and type(out["retracted"]) is not bool:
            raise ValueError("retraction flag must be bool or unknown")
        if origin == "public_api":
            source, article_id = record_id.split(":", 1)
            expected = f"https://europepmc.org/article/{source}/{article_id}"
        else:
            expected = None
    if out["url"] != expected:
        raise ValueError("record URL must be canonical for its ID and origin")
    expected_source = ("ClinicalTrials.gov" if kind == "trial" else "Europe PMC")
    if out["source"] != (expected_source if origin == "public_api" else "SYNTHETIC"):
        raise ValueError("unexpected declared data source")
    return {field:out[field] for field in sorted(out)}


def validate_snapshot(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict) or set(data) != {
        "schema", "query", "origin", "retrieved_at_utc", "records"
    }:
        raise ValueError("invalid snapshot keys")
    if data["schema"] != VERSION or data["origin"] not in ("synthetic", "public_api"):
        raise ValueError("unsupported schema or origin")
    query = valid_query(data["query"])
    when = data["retrieved_at_utc"]
    if data["origin"] == "synthetic":
        if when != "SIMULATED":
            raise ValueError("synthetic inputs must state SIMULATED")
    else:
        if not isinstance(when, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", when):
            raise ValueError("invalid retrieval timestamp")
        try:
            datetime.strptime(when, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ValueError("invalid retrieval timestamp") from exc
    records = data["records"]
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError("too many records")
    cleaned = [_canonical_record(record, data["origin"]) for record in records]
    identity = [(row["kind"], row["id"]) for row in cleaned]
    if len(set(identity)) != len(identity):
        raise ValueError("duplicate source identifier")
    return {"schema": VERSION, "query": query, "origin": data["origin"],
            "retrieved_at_utc": when, "records": sorted(cleaned, key=lambda x:(x["kind"],x["id"]))}


def sample_snapshot() -> Dict[str, Any]:
    """Simulated examples, deliberately NOT actual cancer studies or papers."""
    return {
        "schema": VERSION, "query": "glioblastoma", "origin": "synthetic",
        "retrieved_at_utc": "SIMULATED", "records": [
            {"kind":"trial", "id":"SIM-TRIAL-1", "title":"Simulated early-stage oncology registry",
             "status":"RECRUITING", "phase":"PHASE1", "study_type":"INTERVENTIONAL",
             "results_posted":False, "randomized":None, "updated":"2026-01-01",
             "source":"SYNTHETIC", "url":None},
            {"kind":"trial", "id":"SIM-TRIAL-2", "title":"Simulated later-stage study with results",
             "status":"COMPLETED", "phase":"PHASE3", "study_type":"INTERVENTIONAL",
             "results_posted":True, "randomized":True, "updated":"2025-12-01",
             "source":"SYNTHETIC", "url":None},
            {"kind":"paper", "id":"SIM-PAPER-1", "title":"Simulated preprint awaiting peer review",
             "publication_type":"preprint", "retracted":None,
             "publication_date":"2026-02-10", "source":"SYNTHETIC", "url":None},
        ]
    }


def _retraction(value: Any) -> Optional[bool]:
    if value is True or value == "Y":
        return True
    if value is False or value == "N":
        return False
    return None


def _fetch_json(url: str) -> Dict[str, Any]:
    """Two hardcoded public HTTPS endpoints only. Redirects are forbidden."""
    class NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ValueError("API redirect rejected")
    allowed = (API_TRIALS, API_PAPERS)
    if not any(url.startswith(base + "?") for base in allowed):
        raise ValueError("unexpected API endpoint")
    opener = request.build_opener(NoRedirect())
    req = request.Request(url, headers={
        "User-Agent": "Bio-Gpt-Cure-Swarm/1.0 (bounded public research metadata)",
        "Accept": "application/json",
    })
    with opener.open(req, timeout=12) as response:
        if response.status != 200:
            raise ValueError("public provider returned a non-200 response")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("provider response exceeds size limit")
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("invalid provider payload")
    return result


def _trial_records(raw: Any, cap: int) -> List[Dict[str, Any]]:
    if not isinstance(raw, dict) or not isinstance(raw.get("studies"), list):
        raise ValueError("ClinicalTrials.gov data shape changed")
    records = []
    for item in raw["studies"][:cap]:
        if not isinstance(item, dict):
            continue
        p = item.get("protocolSection", {})
        if not isinstance(p, dict):
            continue
        ident, status, design = p.get("identificationModule", {}), p.get("statusModule", {}), p.get("designModule", {})
        if not all(isinstance(x, dict) for x in (ident, status, design)):
            continue
        nct = ident.get("nctId")
        if not isinstance(nct, str) or not NCT_ID.fullmatch(nct):
            continue
        phases = design.get("phases", [])
        phase = ",".join(short_text(x, 24) for x in phases[:3]) if isinstance(phases, list) else ""
        alloc = design.get("designInfo", {})
        allocation = alloc.get("allocation") if isinstance(alloc, dict) else None
        randomized = True if allocation == "RANDOMIZED" else False if allocation == "NON_RANDOMIZED" else None
        posted = status.get("hasResults")
        flag = posted if type(posted) is bool else True if "resultsSection" in item else None
        posted_date = status.get("lastUpdatePostDateStruct", {})
        updated = (posted_date.get("date", "") if isinstance(posted_date, dict) else "")
        records.append({
            "kind":"trial", "id":nct, "title":short_text(ident.get("briefTitle")) or "Untitled registered study",
            "status":short_text(status.get("overallStatus"), 50),
            "phase":phase, "study_type":short_text(design.get("studyType"), 50),
            "results_posted":flag, "randomized":randomized, "updated":short_text(updated, 30),
            "source":"ClinicalTrials.gov", "url":f"https://clinicaltrials.gov/study/{nct}",
        })
    return records


def _paper_records(raw: Any, cap: int) -> List[Dict[str, Any]]:
    listing = raw.get("resultList") if isinstance(raw, dict) else None
    if not isinstance(listing, dict) or not isinstance(listing.get("result"), list):
        raise ValueError("Europe PMC data shape changed")
    records = []
    for item in listing["result"][:cap]:
        if not isinstance(item, dict):
            continue
        src = item.get("source")
        ident = item.get("id")
        if src not in ("MED", "PMC", "PPR") or not isinstance(ident, str):
            continue
        key = f"{src}:{ident}"
        if not ARTICLE_ID.fullmatch(key):
            continue
        type_name = short_text(item.get("pubType") or ("preprint" if src == "PPR" else "not classified"), 95)
        records.append({
            "kind":"paper", "id":key, "title":short_text(item.get("title")) or "Untitled publication",
            "publication_type":type_name, "retracted":_retraction(item.get("isRetracted")),
            "publication_date":short_text(item.get("firstPublicationDate") or item.get("pubYear"), 32),
            "source":"Europe PMC", "url":f"https://europepmc.org/article/{src}/{ident}",
        })
    return records


def fetch_public_snapshot(query: str, per_source: int = 5,
                          fetch_json: Callable[[str], Dict[str, Any]] = _fetch_json) -> Dict[str, Any]:
    query = valid_query(query)
    if type(per_source) is not int or not 1 <= per_source <= MAX_SOURCE_RESULTS:
        raise ValueError("max per-source records must be 1..10")
    trial_url = API_TRIALS + "?" + parse.urlencode({"query.cond":query,"pageSize":per_source,"format":"json"})
    paper_url = API_PAPERS + "?" + parse.urlencode({"query":query,"pageSize":per_source,
                                                      "resultType":"lite","format":"json"})
    # Fail closed: an API outage is not silently misrepresented as an empty result.
    trials = _trial_records(fetch_json(trial_url), per_source)
    papers = _paper_records(fetch_json(paper_url), per_source)
    data = {"schema":VERSION,"query":query,"origin":"public_api",
            "retrieved_at_utc":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "records":trials + papers}
    return validate_snapshot(data)


def _flags(record: Dict[str, Any]) -> List[str]:
    if record["kind"] == "trial":
        flags = []
        if record["results_posted"] is not True:
            flags.append("RESULTS_NOT_CONFIRMED")
        if "PHASE1" in record["phase"] or "EARLY_PHASE1" in record["phase"]:
            flags.append("EARLY_PHASE")
        if record["status"] in ("TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN"):
            flags.append("STATUS_REQUIRES_REVIEW")
        if record["randomized"] is not True:
            flags.append("RANDOMIZATION_NOT_CONFIRMED")
        return flags or ["FULL_RESULTS_STILL_REQUIRE_APPRAISAL"]
    flags = ["FULL_TEXT_NOT_CRITICALLY_APPRAISED"]
    if record["retracted"] is True:
        flags.append("RETRACTION_SIGNAL_REVIEW")
    if record["retracted"] is None:
        flags.append("RETRACTION_STATUS_UNKNOWN")
    if record["id"].startswith("PPR:") or "preprint" in record["publication_type"].lower():
        flags.append("PREPRINT_NOT_CLINICALLY_VERIFIED")
    return flags


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def analyze(snapshot: Any) -> Dict[str, Any]:
    """Replayable five-stage agent analysis; never a treatment recommendation."""
    normalized = validate_snapshot(snapshot)
    rows = normalized["records"]
    # GPT-Doug: research intake and bounded question definition.
    scout = {"role":"GPT-Doug", "function":"topic_intake", "records":len(rows),
             "disease_topic":normalized["query"], "status":"COMPLETE"}
    # GPT-Pineal: evidence ledger with per-record provenance fingerprints.
    evidence = [{"id":r["id"], "kind":r["kind"], "source":r["source"],
                 "record_sha256":_digest(r), "url":r["url"], "title":r["title"],
                 "review_flags":_flags(r)} for r in rows]
    pineal = {"role":"GPT-Pineal", "function":"provenance_index",
              "records_hashed":len(evidence),"status":"COMPLETE"}
    # GPT-Chaos: adversarial challenges; flags are METADATA gaps, not outcome claims.
    gaps = sorted({flag for entry in evidence for flag in entry["review_flags"]})
    chaos = {"role":"GPT-Doug-Chaos", "function":"counterargument_and_gap_scan",
             "unresolved_flags":gaps,"status":"COMPLETE"}
    # GPT-Doug-Shaggoth: safety and human approval gate.
    policy = {"role":"GPT-Doug-Shaggoth", "function":"human_medical_review_gate",
              "approval":"REQUIRED", "treatment_use":"PROHIBITED",
              "patient_data_processed":False,"clinical_benefit_validated":False,"status":"REVIEW_REQUIRED"}
    # GPT-Doug-Redpanda: bounded coordination/report output, no autonomous activity.
    redpanda = {"role":"GPT-Doug-Redpanda", "function":"bounded_orchestration",
                "agent_runtimes_started":0,"external_actions":0,"status":"COMPLETE"}
    questions = []
    for row in evidence:
        question = ("Verify trial protocol, endpoint results and safety reporting"
                    if row["kind"] == "trial" else
                    "Critically appraise primary evidence, retraction status and reproducibility")
        questions.append({"evidence_id":row["id"],"question":question,
                          "review_required":True})
    report = {
        "name":"Bio-Gpt Cure Swarm", "schema":VERSION,
        "status":"EVIDENCE_CATALOG_REQUIRES_HUMAN_REVIEW",
        "origin":normalized["origin"], "synthetic_demo":normalized["origin"] == "synthetic",
        "input":normalized, "agents":[scout,pineal,chaos,policy,redpanda],
        "evidence":evidence, "research_questions":questions,
        "counts":{"studies":sum(x["kind"] == "trial" for x in rows),
                  "publications":sum(x["kind"] == "paper" for x in rows),
                  "total":len(rows)},
        "caveats":[
            "Evidence metadata alone cannot establish treatment efficacy or safety",
            "Public API entries are untrusted until independently checked against source records",
            "No patient-specific advice, therapy recommendations, dosage or unapproved experiments",
            "A hash proves content consistency, not source authenticity or medical validity",
            "No cure discovered or validated; no biological agents deployed",
        ],
        "network_access_during_analysis":False,
        "operator_approval_required_for_network":True,
        "compute_limits":LIMITS,
        "bio_gpt_link":"six-channel Bio-Hilbert math remains a separate conceptual simulation",
    }
    report["report_sha256"] = _digest(report)
    return report


def compare_snapshots(before: Any, after: Any) -> Dict[str, Any]:
    """Track bounded evidence changes; missing rows might simply be off-page."""
    old, new = validate_snapshot(before), validate_snapshot(after)
    if old["query"] != new["query"] or old["origin"] != new["origin"]:
        raise ValueError("comparison requires the same topic and origin")
    by_id_old = {(r["kind"], r["id"]): r for r in old["records"]}
    by_id_new = {(r["kind"], r["id"]): r for r in new["records"]}
    new_ids = set(by_id_new) - set(by_id_old)
    missing_ids = set(by_id_old) - set(by_id_new)
    changed_ids = {k for k in set(by_id_old) & set(by_id_new)
                   if by_id_old[k] != by_id_new[k]}
    result = {
        "status": "DIFFERENCES_REQUIRE_RESEARCH_REVIEW",
        "topic": old["query"], "origin": old["origin"],
        "previous_snapshot_sha256": _digest(old), "current_snapshot_sha256": _digest(new),
        "new_records": [list(x) for x in sorted(new_ids)],
        "changed_records": [list(x) for x in sorted(changed_ids)],
        "not_in_new_bounded_page": [list(x) for x in sorted(missing_ids)],
        "caveat": "Absent from latest capped query results does not mean study withdrawn or publication deleted",
        "review_required": True,
    }
    result["report_sha256"] = _digest(result)
    return result


def verify(report: Any) -> bool:
    try:
        return isinstance(report, dict) and report == analyze(report["input"])
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def load_json(path: Path) -> Any:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("JSON input exceeds size cap")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="clearly synthetic offline medical evidence example")
    p = sub.add_parser("analyze", help="analyze saved public metadata snapshot offline")
    p.add_argument("file", type=Path)
    v = sub.add_parser("verify", help="replay a saved report exactly")
    v.add_argument("file", type=Path)
    compare = sub.add_parser("compare", help="compare two local snapshots without network access")
    compare.add_argument("previous", type=Path)
    compare.add_argument("current", type=Path)
    online = sub.add_parser("online", help="explicit capped read-only HTTPS metadata fetch")
    online.add_argument("--query", required=True, help="cancer topic, e.g. glioblastoma")
    online.add_argument("--per-source", type=int, default=5, help="1..10 records from each public API")
    online.add_argument("--save-snapshot", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = {"status":"VERIFIED" if verify(load_json(args.file)) else "INVALID"}
            rc = 0 if result["status"] == "VERIFIED" else 1
        elif args.command == "compare":
            result = compare_snapshots(load_json(args.previous), load_json(args.current))
            rc = 0
        else:
            data = (sample_snapshot() if args.command == "demo" else
                    fetch_public_snapshot(args.query, args.per_source) if args.command == "online"
                    else load_json(args.file))
            result, rc = analyze(data), 0
            if args.command == "online" and args.save_snapshot is not None:
                path = args.save_snapshot
                if path.is_symlink() or path.exists():
                    raise ValueError("snapshot destination must be a new regular file path")
                # Avoid accidentally creating world-readable medical metadata archives.
                import os
                fd = os.open(path, os.O_WRONLY | os.O_EXCL | os.O_CREAT, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, sort_keys=True)
                    handle.write("\n")
        print(json.dumps(result, indent=2, sort_keys=True))
        return rc
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, json.JSONDecodeError, error.URLError) as exc:
        print(json.dumps({"status":"ERROR", "kind":type(exc).__name__,
                          "note":"Public source may be unavailable; no partial evidence was certified"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
