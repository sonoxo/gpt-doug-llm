#!/usr/bin/env python3
"""Evidence-first federal contracting readiness auditor. Standard library only.

This tool is advisory, does not authenticate to federal systems, and never
infers registration, eligibility, clearance, or compliance from source code.
"""
import argparse
import datetime as dt
import json
import pathlib
import urllib.error
import urllib.request

GATES = {
 "business": ("Entity registration / SAM.gov", ["legal_entity_record", "sam_active_record", "uei", "cage"]),
 "capability": ("Agency-specific capability statement", ["capability_statement", "claims_review"]),
 "demo": ("Reproducible technical demonstration", ["demo_instructions", "test_results", "deployment_evidence"]),
 "security": ("Security and compliance assessment", ["security_assessment", "control_mapping", "risk_approvals"]),
 "performance": ("Past performance and personnel", ["client_references", "past_deliverables", "personnel_qualifications"]),
 "clearance": ("Clearance / facility and teaming", ["facility_clearance_verification", "teaming_agreement"]),
}
OFFICIAL = {
 "business": ["https://sam.gov/content/entity-registration", "https://www.sba.gov/federal-contracting"],
 "capability": ["https://www.sba.gov/federal-contracting/contracting-guide"],
 "demo": ["https://www.nist.gov/itl/ssd/software-quality-group"],
 "security": ["https://csrc.nist.gov/projects/risk-management", "https://www.acq.osd.mil/asda/dpc/cp/cyber/cybersecurity-maturity-model-certification.html"],
 "performance": ["https://www.sba.gov/federal-contracting/contracting-guide"],
 "clearance": ["https://www.dcsa.mil/Industrial-Security/Entity-Vetting-Facility-Clearances/"],
}
# This is observational metadata, not an attestation of federal readiness.
def repo_metadata(repo, timeout=8):
    if not repo or "/" not in repo:
        return {"status": "not_requested"}
    url = "https://api.github.com/repos/" + repo
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "federal-readiness-audit"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = json.load(res)
        return {"status": "observed", "repository": data.get("full_name"), "visibility": "private" if data.get("private") else "public", "default_branch": data.get("default_branch"), "updated_at": data.get("pushed_at"), "url": data.get("html_url")}
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}

def audit(manifest, repository=None):
    attested = manifest.get("evidence", {})
    output = {}
    for key, (title, needed) in GATES.items():
        items, complete = {}, True
        for field in needed:
            entry = attested.get(key, {}).get(field, {})
            # Verified must be explicitly reviewed and carry an evidence reference.
            good = isinstance(entry, dict) and entry.get("reviewed") is True and entry.get("status") == "verified" and isinstance(entry.get("reference"), str) and bool(entry["reference"].strip()) and isinstance(entry.get("reviewer"), str) and bool(entry["reviewer"].strip())
            items[field] = {"status": "verified" if good else "unverified", "reference": entry.get("reference") if good else None}
            complete = complete and good
        output[key] = {"name": title, "status": "evidence_reviewed" if complete else "incomplete", "evidence": items, "official_sources": OFFICIAL[key]}
    return {"schema_version": 1, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "evidence_review_only", "warning": "Reviewer assertions are not agency certification. Independently confirm registration, authorization, past performance and clearance using official channels.", "gates": output, "github": repo_metadata(repository) if repository else {"status": "not_requested"}}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=pathlib.Path, help="Locally stored JSON evidence manifest; never commit confidential records")
    p.add_argument("--repository", default=None, help="Optional owner/repo for public GitHub metadata")
    p.add_argument("--output", type=pathlib.Path, help="Optional report JSON path")
    args = p.parse_args()
    data = json.loads(args.manifest.read_text()) if args.manifest else {"evidence": {}}
    result = audit(data, args.repository)
    blob = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(blob)
    print(blob, end="")

if __name__ == "__main__":
    main()
