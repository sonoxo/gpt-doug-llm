"""Offline regressions for public-source intelligence freshness and evidence gates."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.request import Request

from agency_cloud.global_intel import (
    SOURCE_DEFINITIONS, _point, _swpc, _validate_source_url,
    _PublicSourceRedirectHandler, build_benchmark, score_probe,
)
from agency_cloud.intel_evidence import EvidenceError, SCHEMA, main, summarize_benchmark


NOW = datetime(2026, 10, 14, 16, 0, tzinfo=timezone.utc)


def probe(index: int, *, fetched: datetime | None = NOW,
          observed: datetime | None = NOW, status: str = "ONLINE") -> dict:
    row = dict(SOURCE_DEFINITIONS[index])
    row.update({
        "status": status, "schemaValid": status == "ONLINE",
        "fetchedAt": fetched.isoformat() if fetched else None,
        "observedAt": observed.isoformat() if observed else None,
        "summary": {"count": index + 1, "mode": "public synthetic regression"},
        "score": 99 if status == "ONLINE" else 0,
    })
    return row


def benchmark(*items: dict) -> dict:
    return {
        "schema": "gpt-doug.global-intel-benchmark.v1",
        "generatedAt": NOW.isoformat(),
        "sources": list(items),
        "mapPoints": [{"longitude": -70, "latitude": 10,
                       "title": "NOT FOR EVIDENCE EXPORT"}],
        "signals": {"not_proven": {"raw": "omitted"}},
    }


class IntelEvidenceTests(unittest.TestCase):
    def test_real_source_catalog_size(self):
        self.assertEqual(len(SOURCE_DEFINITIONS), 5)

    def test_trustworthy_metadata_preserved_without_claim_promotion(self):
        result = summarize_benchmark(benchmark(probe(0), probe(1)), evaluated_at=NOW)
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["sourceCount"], 2)
        self.assertEqual(result["rejectedSourceCount"], 0)
        self.assertEqual(result["coverage"]["claimsIndependentlyCorroborated"], 0)
        self.assertEqual(result["coverage"]["feedStates"]["RECENT_FETCH"], 2)
        self.assertEqual(result["sources"][0]["claimState"], "SOURCE_STATEMENT_UNCORROBORATED")
        self.assertEqual(result["sources"][0]["analyticConfidence"], "NOT_ASSESSED")
        self.assertEqual(result["sources"][0]["fetchState"], "RECENT_FETCH")
        self.assertEqual(len(result["ontology"]["edges"]), 2)
        self.assertEqual(result["policy"]["automaticBlocking"], False)
        self.assertEqual(result["policy"]["militaryTracking"], False)
        self.assertNotIn("mapPoints", json.dumps(result))
        self.assertNotIn("NOT FOR EVIDENCE EXPORT", json.dumps(result))

    def test_deterministic_for_fixed_assessment_time(self):
        src = benchmark(probe(1), probe(0))
        one = summarize_benchmark(src, evaluated_at=NOW)
        two = summarize_benchmark(src, evaluated_at=NOW)
        self.assertEqual(one, two)
        self.assertEqual(one["snapshotSha256"], two["snapshotSha256"])
        self.assertEqual([x["sourceId"] for x in one["sources"]],
                         sorted(x["sourceId"] for x in one["sources"]))

    def test_age_is_about_latest_entry_not_source_website(self):
        result = summarize_benchmark(
            benchmark(probe(3, observed=NOW-timedelta(days=10))),
            evaluated_at=NOW,
        )
        item = result["sources"][0]
        self.assertEqual(item["fetchState"], "RECENT_FETCH")
        self.assertEqual(item["lastEntryState"], "LAST_ENTRY_OLDER_THAN_EXPECTED")
        self.assertIn("not feed last-modified", item["lastEntryTimeMeaning"])

    def test_degraded_source_does_not_claim_online(self):
        result = summarize_benchmark(benchmark(probe(0, status="DEGRADED")), evaluated_at=NOW)
        self.assertEqual(result["sources"][0]["fetchState"], "FETCH_FAILED")
        self.assertEqual(result["sources"][0]["reviewDecision"], "REVIEW_REQUIRED")

    def test_fetch_cache_age_and_future_clock_skew_are_separate(self):
        old = probe(0, fetched=NOW-timedelta(minutes=30))
        future = probe(1, fetched=NOW+timedelta(hours=1))
        result = summarize_benchmark(benchmark(old, future), evaluated_at=NOW)
        states = {x["sourceId"]: x["fetchState"] for x in result["sources"]}
        self.assertEqual(states["usgs-earthquakes"], "FETCH_STALE")
        self.assertEqual(states["nasa-eonet"], "FUTURE_FETCH_CLOCK_SKEW")

    def test_future_entry_timestamp_flagged(self):
        result = summarize_benchmark(
            benchmark(probe(0, observed=NOW+timedelta(hours=1))), evaluated_at=NOW
        )
        self.assertEqual(result["sources"][0]["lastEntryState"], "FUTURE_ENTRY_CLOCK_SKEW")

    def test_unknown_timestamps_are_not_described_as_fresh(self):
        result = summarize_benchmark(benchmark(probe(0, fetched=None, observed=None)),
                                     evaluated_at=NOW)
        self.assertEqual(result["sources"][0]["fetchState"], "FETCH_TIME_UNKNOWN")
        self.assertEqual(result["sources"][0]["lastEntryState"], "ENTRY_TIME_UNKNOWN")

    def test_rejects_spoofed_authority_and_new_source_and_duplicate(self):
        good = probe(0)
        altered = probe(1)
        altered["url"] = "https://attacker.example/forged.json"
        unknown = probe(2)
        unknown["id"] = "not-approved"
        result = summarize_benchmark(benchmark(good, good, altered, unknown),
                                     evaluated_at=NOW)
        self.assertEqual(result["sourceCount"], 1)
        self.assertEqual(result["rejectedSourceCount"], 3)
        self.assertEqual({r["reason"] for r in result["rejected"]},
                         {"DUPLICATE_SOURCE_ID", "SOURCE_PROVENANCE_MISMATCH",
                          "SOURCE_ID_NOT_APPROVED"})
        self.assertNotIn("attacker.example", json.dumps(result))

    def test_reject_bad_schema_and_naive_datetime(self):
        with self.assertRaises(EvidenceError):
            summarize_benchmark({"schema": "untrusted", "sources": []}, evaluated_at=NOW)
        with self.assertRaises(EvidenceError):
            summarize_benchmark(benchmark(probe(0)), evaluated_at=datetime(2026, 10, 14))

    def test_reject_nonfinite_unbounded_and_non_dict_summary(self):
        item = probe(0)
        item["summary"] = {"nonfinite": float("nan")}
        result = summarize_benchmark(benchmark(item), evaluated_at=NOW)
        self.assertEqual(result["rejectedSourceCount"], 1)
        item["summary"] = {"extra": "a" * 41000}
        result = summarize_benchmark(benchmark(item), evaluated_at=NOW)
        self.assertEqual(result["rejectedSourceCount"], 1)
        item["summary"] = ["not a JSON object"]
        result = summarize_benchmark(benchmark(item), evaluated_at=NOW)
        self.assertEqual(result["rejectedSourceCount"], 1)

    def test_geospatial_coordinates_must_be_finite(self):
        self.assertIsNone(_point("usgs-earthquakes", "bad", "NATURAL", float("nan"), 30))
        self.assertIsNone(_point("usgs-earthquakes", "bad", "NATURAL", 20, float("inf")))
        self.assertIsNotNone(_point("usgs-earthquakes", "good", "NATURAL", 20, 30))

    def test_swpc_nonfinite_index_never_enters_response(self):
        parsed = _swpc([["time_tag", "kp_index"], ["2026-10-14T15:00:00Z", "NaN"]])
        self.assertIsNone(parsed["summary"]["planetaryKp"])
        self.assertIsNone(parsed["summary"]["stormScale"])

    def test_source_host_and_redirect_https_enforcement(self):
        _validate_source_url("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson")
        for url in ("http://earthquake.usgs.gov/feed",
                    "https://attacker.example/feed",
                    "https://earthquake.usgs.gov:444/feed",
                    "https://alice:secret@earthquake.usgs.gov/feed"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                _validate_source_url(url)
        h = _PublicSourceRedirectHandler()
        req = Request("https://earthquake.usgs.gov/initial")
        with self.assertRaises(ValueError):
            h.redirect_request(req, None, 302, "Found", {},
                               "https://attacker.example/untrusted")

    def test_future_dated_score_fails_freshness_dimension(self):
        score, detail = score_probe(
            available=True, schema_valid=True, latency_ms=50,
            observed_at=datetime.now(timezone.utc)+timedelta(days=2),
            expected_freshness_seconds=1800, cadence="minutes"
        )
        self.assertEqual(detail["freshness"], 0)
        self.assertLess(score, 90)

    def test_yearly_data_with_no_date_gets_no_unearned_freshness(self):
        _, detail = score_probe(available=True, schema_valid=True, latency_ms=100,
                                observed_at=None, expected_freshness_seconds=94608000,
                                cadence="annual")
        self.assertLess(detail["freshness"], 20)

    def test_offline_cli_writes_and_respects_force(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            target = Path(tmp) / "output.json"
            source.write_text(json.dumps(benchmark(probe(0))), encoding="utf-8")
            self.assertEqual(main(["--input", str(source), "--output", str(target)]), 0)
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc["sourceCount"], 1)
            self.assertEqual(main(["--input", str(source), "--output", str(target)]), 2)
            self.assertEqual(main(["--input", str(source), "--output", str(target), "--force"]), 0)

    def test_refuses_network_or_physical_actions(self):
        result = summarize_benchmark(benchmark(probe(0)), evaluated_at=NOW)
        self.assertTrue(result["policy"]["readOnly"])
        self.assertFalse(result["policy"]["externalActions"])
        self.assertFalse(result["policy"]["targeting"])
        self.assertTrue(result["policy"]["humanReviewRequired"])


if __name__ == "__main__":
    unittest.main()
