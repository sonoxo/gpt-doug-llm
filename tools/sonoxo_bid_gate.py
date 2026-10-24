#!/usr/bin/env python3
"""Read-only bid-readiness verifier. NEVER submits bids or contacts buyers."""
import argparse
import json
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / "procurement" / "2026-10-16" / "requirements.json"
VALID_SOURCE = {"official_notice", "annex_unavailable", "buyer_conditions_unverified"}
VALID_STATUS = {"missing", "verified", "not_applicable"}

def assess(opportunity, overlay=None):
    """Return a conservative manual-review gate for one prospective bid."""
    overlay = overlay or {}
    known = {r["id"] for r in opportunity["requirements"]}
    if set(overlay) - known:
        raise ValueError("Evidence overlay references unknown requirement IDs")
    blockers = []
    for r in opportunity["requirements"]:
        if r["source_status"] not in VALID_SOURCE:
            raise ValueError("Unknown source status")
        update = overlay.get(r["id"], {})
        if set(update) - {"bidder_status", "evidence_ref", "official_annex_url"}:
            raise ValueError("Unsupported evidence field")
        status = update.get("bidder_status", r["bidder_status"])
        evidence_ref = str(update.get("evidence_ref", r["evidence_ref"])).strip()
        official_annex = str(update.get("official_annex_url", "")).strip()
        if status not in VALID_STATUS:
            raise ValueError("Invalid bidder evidence status")
        if not r["blocking"]:
            continue
        if r["source_status"] != "official_notice" and not official_annex:
            blockers.append({"id": r["id"], "reason": "Governing requirement/annex unverified"})
        if status != "verified" or not evidence_ref:
            blockers.append({"id": r["id"], "reason": "No verified company evidence"})
    return {
        "opportunity_id": opportunity["id"],
        "deadline": opportunity["deadline"],
        "timezone": opportunity["timezone"],
        "decision": "ready_for_manual_bid_review" if not blockers else "blocked_do_not_submit",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "source_url": opportunity["official_url"],
        "note": "This software cannot certify eligibility or submit anything. Independent human and buyer review required.",
    }

def main():
    p = argparse.ArgumentParser(description="Read-only procurement compliance gate")
    p.add_argument("--requirements", type=Path, default=DEFAULT)
    p.add_argument("--evidence", type=Path, help="Local-only JSON keyed by opportunity ID then requirement ID")
    p.add_argument("--id", help="Only one opportunity ID")
    p.add_argument("--output", type=Path, help="Optional path to local JSON report")
    args = p.parse_args()
    raw = json.loads(args.requirements.read_text(encoding="utf-8"))
    if raw.get("schema") != "sonoxo.procurement.requirements.v1":
        p.error("Unexpected requirements schema")
    overlay = json.loads(args.evidence.read_text(encoding="utf-8")) if args.evidence else {}
    if not isinstance(overlay, dict):
        p.error("Evidence must be a JSON object")
    selected = [op for op in raw["opportunities"] if args.id is None or op["id"] == args.id]
    if not selected:
        p.error("Unknown opportunity ID")
    reports = [assess(op, overlay.get(op["id"], {})) for op in selected]
    output = json.dumps({"schema":"sonoxo.procurement.readiness.v1","results":reports}, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)

if __name__ == "__main__":
    main()
