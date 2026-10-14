"""Independent public-source evidence health for the GPT-Doug Global Intel service.

This is an engineering assessment of feed retrieval/metadata freshness, NOT an
assessment of military threat, political risk, the truth of content, or analyst
confidence. It neither fetches sources nor controls external systems.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping

from .global_intel import CACHE_TTL_SECONDS, SOURCE_DEFINITIONS

SCHEMA = "gpt-doug.global-intel-evidence.v1"
INPUT_SCHEMA = "gpt-doug.global-intel-benchmark.v1"
SOURCE_BY_ID = {str(source["id"]): source for source in SOURCE_DEFINITIONS}
FETCH_FRESHNESS_SECONDS = max(900, CACHE_TTL_SECONDS * 2)
MAX_FUTURE_SKEW_SECONDS = 300
MAX_SOURCES = 32
MAX_SUMMARY_BYTES = 40_000

OBSERVED_TIME_MEANING = {
    "usgs-earthquakes": "USGS feed metadata.generated timestamp",
    "nasa-eonet": "latest event geometry timestamp, not last API update",
    "noaa-swpc-kp": "latest reported K-index observation",
    "cisa-kev": "latest catalog vulnerability dateAdded, not feed last-modified",
    "world-bank-internet": "end of indicator reporting year, not API update",
}

POLICY = {
    "classification": "PUBLIC_SOURCE_ONLY",
    "readOnly": True,
    "automaticBlocking": False,
    "externalActions": False,
    "militaryTracking": False,
    "privatePersonTracking": False,
    "targeting": False,
    "humanReviewRequired": True,
    "independentClaimCorroboration": False,
    "dataQualityIsNotThreatSeverity": True,
    "availabilityIsNotTruth": True,
}


class EvidenceError(ValueError):
    """Unsupported or unsafe benchmark input."""


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 80:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None


def _utc(at: datetime | None) -> datetime:
    if at is None:
        return datetime.now(timezone.utc)
    if not isinstance(at, datetime) or at.tzinfo is None:
        raise EvidenceError("assessment time must be timezone-aware")
    return at.astimezone(timezone.utc)


def _seconds_between(later: datetime, earlier: datetime | None) -> int | None:
    if earlier is None:
        return None
    return int((later - earlier).total_seconds())


def _digest(summary: Mapping[str, Any]) -> str:
    try:
        canonical = json.dumps(summary, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EvidenceError("summary contains unsupported or nonfinite values") from exc
    if len(canonical.encode("utf-8")) > MAX_SUMMARY_BYTES:
        raise EvidenceError("summary exceeds data minimization limit")
    return sha256(canonical.encode("utf-8")).hexdigest()


def summarize_benchmark(benchmark: Mapping[str, Any], *, evaluated_at: datetime | None = None) -> dict:
    """Convert a Global Intel benchmark into a bounded, provenance-first graph.

    Only recognized first-party public source IDs/URLs are indexed. The graph
    records source-supplied summaries, not verified facts, independent source
    corroboration, raw geospatial objects, or personal information.
    """
    now = _utc(evaluated_at)
    if not isinstance(benchmark, Mapping) or benchmark.get("schema") != INPUT_SCHEMA:
        raise EvidenceError("expected Global Intel benchmark v1")
    incoming = benchmark.get("sources")
    if not isinstance(incoming, list) or len(incoming) > MAX_SOURCES:
        raise EvidenceError("invalid or oversized source collection")

    observed: list[dict] = []
    rejected: list[dict] = []
    seen = set()
    for index, probe in enumerate(incoming):
        if not isinstance(probe, Mapping):
            rejected.append({"index": index, "reason": "NOT_A_SOURCE_OBJECT"})
            continue
        sid = probe.get("id")
        if not isinstance(sid, str) or sid not in SOURCE_BY_ID:
            rejected.append({"index": index, "reason": "SOURCE_ID_NOT_APPROVED"})
            continue
        if sid in seen:
            rejected.append({"index": index, "reason": "DUPLICATE_SOURCE_ID"})
            continue
        seen.add(sid)
        expected = SOURCE_BY_ID[sid]
        if (probe.get("url") != expected["url"]
                or probe.get("domain") != expected["domain"]
                or probe.get("authority") != expected["authority"]):
            rejected.append({"index": index, "reason": "SOURCE_PROVENANCE_MISMATCH"})
            continue
        status = probe.get("status")
        if status not in ("ONLINE", "DEGRADED"):
            rejected.append({"index": index, "reason": "INVALID_STATUS"})
            continue
        summary = probe.get("summary", {})
        if not isinstance(summary, Mapping):
            rejected.append({"index": index, "reason": "INVALID_SUMMARY"})
            continue
        try:
            digest = _digest(summary)
        except EvidenceError:
            rejected.append({"index": index, "reason": "INVALID_SUMMARY"})
            continue

        fetched = _date(probe.get("fetchedAt"))
        last_observed = _date(probe.get("observedAt"))
        fetch_age = _seconds_between(now, fetched)
        last_entry_age = _seconds_between(now, last_observed)
        if status == "DEGRADED":
            feed_state = "FETCH_FAILED"
        elif fetch_age is None:
            feed_state = "FETCH_TIME_UNKNOWN"
        elif fetch_age < -MAX_FUTURE_SKEW_SECONDS:
            feed_state = "FUTURE_FETCH_CLOCK_SKEW"
        elif fetch_age > FETCH_FRESHNESS_SECONDS:
            feed_state = "FETCH_STALE"
        else:
            feed_state = "RECENT_FETCH"

        allowed_age = int(expected["expectedFreshnessSeconds"])
        if last_entry_age is None:
            data_state = "ENTRY_TIME_UNKNOWN"
        elif last_entry_age < -MAX_FUTURE_SKEW_SECONDS:
            data_state = "FUTURE_ENTRY_CLOCK_SKEW"
        elif last_entry_age > allowed_age:
            data_state = "LAST_ENTRY_OLDER_THAN_EXPECTED"
        else:
            data_state = "LAST_ENTRY_WITHIN_EXPECTED_AGE"

        node_id = "evidence/" + sid + "/" + digest[:16]
        observed.append({
            "sourceId": sid, "authority": expected["authority"], "domain": expected["domain"],
            "canonicalUrl": expected["url"], "cadence": expected["cadence"],
            "fetchState": feed_state, "lastEntryState": data_state,
            "fetchedAt": fetched.isoformat() if fetched else None,
            "lastEntryAt": last_observed.isoformat() if last_observed else None,
            "fetchAgeSeconds": fetch_age,
            "lastEntryAgeSeconds": last_entry_age,
            "expectedLastEntryAgeSeconds": allowed_age,
            "lastEntryTimeMeaning": OBSERVED_TIME_MEANING[sid],
            "summarySha256": digest,
            "summaryDigestMeaning": "sha256-normalized-parser-summary-not-raw-source-content",
            "evidenceId": node_id,
            "claimState": "SOURCE_STATEMENT_UNCORROBORATED",
            "independentCorroboration": "NOT_PERFORMED",
            "analyticConfidence": "NOT_ASSESSED",
            "sourceFitnessScore": probe.get("score") if isinstance(probe.get("score"), int) and not isinstance(probe.get("score"), bool) and 0 <= probe["score"] <= 100 else None,
            "reviewDecision": "REVIEW_REQUIRED",
        })
    observed.sort(key=lambda x: x["sourceId"])
    flags = Counter(obs["fetchState"] for obs in observed)
    data_flags = Counter(obs["lastEntryState"] for obs in observed)
    source_nodes = [{"id": "source/" + obs["sourceId"], "type": "PublicSource",
                     "sourceId": obs["sourceId"], "url": obs["canonicalUrl"]}
                    for obs in observed]
    evidence_nodes = [{"id": obs["evidenceId"], "type": "ParsedSourceSummary",
                       "sourceId": obs["sourceId"], "sha256": obs["summarySha256"],
                       "reviewState": obs["reviewDecision"]} for obs in observed]
    edges = [{"source": "source/" + obs["sourceId"], "target": obs["evidenceId"],
              "relation": "HAS_UNVERIFIED_PARSER_SUMMARY"} for obs in observed]
    result = {
        "schema": SCHEMA, "assessedAt": now.isoformat(),
        "benchmarkGeneratedAt": _date(benchmark.get("generatedAt")).isoformat() if _date(benchmark.get("generatedAt")) else None,
        "sourceCount": len(observed), "rejectedSourceCount": len(rejected),
        "rejected": rejected,
        "coverage": {
            "feedStates": dict(sorted(flags.items())),
            "lastEntryStates": dict(sorted(data_flags.items())),
            "sourcesWithRecognizedProvenance": len(observed),
            "claimsIndependentlyCorroborated": 0,
        },
        "sources": observed,
        "ontology": {"nodes": source_nodes + evidence_nodes, "edges": edges,
                     "relationSemantics": "source-to-uncorroborated-parsed-summary"},
        "policy": POLICY,
        "judgment": "REVIEW_REQUIRED",
        "disclaimer": "Feed retrieval and recent entries do not validate factual claims or warrant operations.",
    }
    result["snapshotSha256"] = _digest_snapshot(result)
    return result


def _digest_snapshot(value: Mapping[str, Any]) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="existing benchmark JSON; no network")
    parser.add_argument("--output", type=Path, help="local evidence graph JSON")
    parser.add_argument("--force", action="store_true", help="overwrite local output only")
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file() or args.input.stat().st_size > 1_000_000:
            raise EvidenceError("input file missing or oversized")
        input_data = json.loads(args.input.read_text(encoding="utf-8"))
        result = summarize_benchmark(input_data)
        payload = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        if args.output:
            if args.output.exists() and not args.force:
                raise EvidenceError("output exists; use --force to replace the local file")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
            print(json.dumps({"ok": True, "output": str(args.output),
                              "sourceCount": result["sourceCount"],
                              "rejectedSourceCount": result["rejectedSourceCount"],
                              "remoteActions": 0}))
        else:
            sys.stdout.write(payload)
        return 0
    except (EvidenceError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "networkActions": 0}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
