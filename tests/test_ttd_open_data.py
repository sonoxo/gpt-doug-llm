"""Isolation tests for opt-in public-data sources and randomized snapshots."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import types
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ttd_llm.engine import DataCatalog, TTDValidationError
from ttd_llm.open_data import (
    OpenDataError, SOURCES, Source, _items, choose_sources, fetch_source,
    run, synchronize,
)


class OpenDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.payloads = {
            "usgs_earthquakes": {
                "features": [
                    {"id": "eq1", "properties": {"title": "M 4.2 - Test Region",
                         "place": "Test Region", "time": 1791900000000,
                         "mag": 4.2, "url": "https://earthquake.usgs.gov/earthquakes/eventpage/eq1"}},
                    {"id": "eq2", "properties": {"title": "DROP TABLE open_records; --",
                         "place": "Test Region 2", "time": 1791900000000,
                         "mag": 3.4, "url": "http://invalid.example/callback"}},
                ]
            },
            "nasa_eonet": {"events": [
                {"id": "EONET_1", "title": "Observed Wildfire",
                 "categories": [{"title": "Wildfires"}],
                 "geometry": [{"date": "2026-10-12T12:00:00Z"}]},
            ]},
            "worldbank_population": [
                {"page": 1},
                [{"countryiso3code": "USA", "date": "2025",
                  "country": {"value": "United States"}, "value": 340000000},
                 {"countryiso3code": "", "date": "2025",
                  "country": {"value": "World"}, "value": 8000000000}],
            ],
            "worldbank_gdp": [
                {"page": 1},
                [{"countryiso3code": "FRA", "date": "2025",
                  "country": {"value": "France"}, "value": 3100000000000}],
            ],
            "openalex_works": {"results": [
                {"id": "https://openalex.org/W123", "title": "Open research",
                 "publication_date": "2026-10-01", "cited_by_count": 42},
            ]},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def fake_fetch(self, source):
        return self.payloads[source.key], "c" * 64

    def test_source_listing_never_accesses_network(self):
        with patch("ttd_llm.open_data.fetch_source", side_effect=AssertionError("network")):
            response = run(["sources"])
        self.assertEqual(response["network_calls"], 0)
        self.assertEqual(len(response["sources"]), 5)
        self.assertTrue(all(s["endpoint"].startswith("https://") for s in response["sources"]))

    def test_dry_run_randomization_no_io(self):
        path = self.dir / "missing.db"
        result = run(["sync", "--all", "--db", str(path), "--randomize",
                      "--seed", "991", "--sample-sources", "2", "--dry-run"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["network_calls"], 0)
        self.assertEqual(len(result["selected_sources"]), 2)
        self.assertEqual(result, run(["sync", "--all", "--db", str(path),
                                     "--randomize", "--seed", "991",
                                     "--sample-sources", "2", "--dry-run"]))
        self.assertFalse(path.exists())

    def test_unknown_source_and_selection_guards(self):
        for keys, kw in [(["unknown"], {}), (["nasa_eonet", "nasa_eonet"], {}),
                         (["nasa_eonet"], {"seed": 2}),
                         (["nasa_eonet"], {"randomize": True, "sample_sources": 2})]:
            with self.subTest(keys=keys, kw=kw), self.assertRaises(OpenDataError):
                choose_sources(keys, **kw)
        with self.assertRaises(OpenDataError):
            synchronize(["nasa_eonet"], self.dir / "a.db", max_records=300, fetcher=self.fake_fetch)

    def test_all_five_feeds_produce_readonly_citable_sqlite(self):
        path = self.dir / "open.sqlite3"
        result = synchronize(list(SOURCES), path, max_records=30, fetcher=self.fake_fetch)
        self.assertTrue(result["ok"])
        self.assertEqual(result["sources_imported"], 5)
        self.assertEqual(result["records_imported"], 6)
        with closing(sqlite3.connect(path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM source_receipts").fetchone()[0], 5)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM open_records").fetchone()[0], 6)
            self.assertEqual(conn.execute("SELECT response_sha256 FROM source_receipts WHERE source_id='nasa_eonet'").fetchone()[0], "c" * 64)
        with DataCatalog(path, tables=["open_records"]) as catalog:
            summary = catalog.execute({
                "table": "open_records", "group_by": ["source_id"],
                "aggregate": {"function": "count", "column": "*"},
                "order_by": {"column": "source_id", "direction": "asc"},
            })
            self.assertEqual({x["source_id"]: x["metric"] for x in summary["rows"]}, {
                "nasa_eonet": 1, "openalex_works": 1, "usgs_earthquakes": 2,
                "worldbank_gdp": 1, "worldbank_population": 1,
            })
            self.assertIn("source_id", catalog.schema()["tables"]["open_records"])
            self.assertIn("LIMIT ?", summary["evidence"]["sql"])
            with self.assertRaises(TTDValidationError):
                catalog.execute({"table": "source_receipts", "select": ["response_sha256"]})
            with self.assertRaises(sqlite3.OperationalError):
                catalog.conn.execute("DELETE FROM open_records")

    def test_cross_unit_aggregate_requires_measure(self):
        path = self.dir / "open.db"
        synchronize(["usgs_earthquakes", "worldbank_population"], path,
                    fetcher=self.fake_fetch)
        with DataCatalog(path, tables=["open_records"]) as catalog:
            with self.assertRaises(TTDValidationError):
                catalog.execute({"table": "open_records", "aggregate": {
                    "function": "sum", "column": "metric_value"}})
            answer = catalog.execute({"table": "open_records", "aggregate": {
                "function": "avg", "column": "metric_value"}, "filters": [
                {"column": "measure", "op": "eq", "value": "earthquake_magnitude"}]})
            self.assertAlmostEqual(answer["rows"][0]["metric"], 3.8)

    def test_untrusted_titles_and_urls_cannot_execute_or_exfiltrate(self):
        path = self.dir / "open.db"
        synchronize(["usgs_earthquakes"], path, fetcher=self.fake_fetch)
        with DataCatalog(path, tables=["open_records"]) as catalog:
            result = catalog.execute({"table": "open_records", "select": ["title", "record_url"],
                                      "filters": [{"column": "title", "op": "contains",
                                                   "value": "DROP TABLE"}]})
            self.assertEqual(result["rows"][0]["title"], "DROP TABLE open_records; --")
            self.assertTrue(result["rows"][0]["record_url"].startswith("https://earthquake.usgs.gov/"))
            self.assertNotIn("DROP TABLE", result["evidence"]["sql"])

    def test_repeatable_seeded_random_sample(self):
        self.payloads["usgs_earthquakes"]["features"] = [
            {"id": "eq" + str(i), "properties": {"title": "Earthquake " + str(i),
             "place": "Test", "time": 1791900000000, "mag": float(i)}} for i in range(20)
        ]
        first, second = self.dir / "a.db", self.dir / "b.db"
        a = synchronize(["usgs_earthquakes", "nasa_eonet"], first,
                        randomize=True, seed=934, max_records=3, fetcher=self.fake_fetch)
        b = synchronize(["usgs_earthquakes", "nasa_eonet"], second,
                        randomize=True, seed=934, max_records=3, fetcher=self.fake_fetch)
        self.assertEqual(a["selected_sources"], b["selected_sources"])
        self.assertEqual(a["seed"], 934)
        with closing(sqlite3.connect(first)) as ca, closing(sqlite3.connect(second)) as cb:
            sql = "SELECT source_id, record_id FROM open_records ORDER BY source_id, record_id"
            self.assertEqual(ca.execute(sql).fetchall(), cb.execute(sql).fetchall())
            self.assertEqual(ca.execute("SELECT COUNT(*) FROM open_records").fetchone()[0], 4)

    def test_partial_failure_explicit_and_fail_closed_on_total_failure(self):
        db = self.dir / "partial.db"
        def partial(spec):
            if spec.key == "nasa_eonet":
                raise OpenDataError("offline")
            return self.fake_fetch(spec)
        res = synchronize(["nasa_eonet", "worldbank_population"], db, fetcher=partial)
        self.assertTrue(res["partial"])
        self.assertEqual(res["sources_imported"], 1)
        self.assertEqual(res["source_failures"], [{"source": "nasa_eonet", "error": "OpenDataError"}])
        old = db.read_bytes()
        with self.assertRaises(OpenDataError):
            synchronize(["nasa_eonet"], db, replace=True, fetcher=partial)
        self.assertEqual(db.read_bytes(), old)

    def test_preexisting_files_and_symlinks_protected(self):
        path = self.dir / "occupied.db"
        path.write_bytes(b"not a snapshot")
        with self.assertRaises(OpenDataError):
            synchronize(["nasa_eonet"], path, fetcher=self.fake_fetch)
        self.assertEqual(path.read_bytes(), b"not a snapshot")
        symlink = self.dir / "link.db"
        symlink.symlink_to(path)
        with self.assertRaises(OpenDataError):
            synchronize(["nasa_eonet"], symlink, replace=True, fetcher=self.fake_fetch)
        self.assertEqual(path.read_bytes(), b"not a snapshot")

    def test_malformed_feed_rejected(self):
        with self.assertRaises(OpenDataError):
            _items(SOURCES["nasa_eonet"], {"events": ["not an event"]})
        with self.assertRaises(OpenDataError):
            _items(SOURCES["openalex_works"], {"results": [{}] * 501})
        with self.assertRaises(OpenDataError):
            _items(SOURCES["worldbank_population"], {"results": []})

    def test_read_only_registry_rejects_lookalike_source(self):
        source = SOURCES["usgs_earthquakes"]
        altered = Source(source.key, source.publisher, source.category,
                         "https://evil.example/private", source.documentation,
                         source.measure, source.unit)
        with self.assertRaises(OpenDataError):
            fetch_source(altered)

    @patch("ttd_llm.open_data.urllib.request.build_opener")
    def test_cross_host_redirect_result_refused(self, opener):
        source = SOURCES["nasa_eonet"]
        class Response:
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def geturl(self): return "https://bad.example/final"
            def read(self, size): return b"{}"
        opener.return_value.open.return_value = Response()
        mock_stop = types.ModuleType("ai_killswitch")
        mock_stop.require_ai_allowed = lambda *_: None
        with patch.dict(sys.modules, {"ai_killswitch": mock_stop}):
            with self.assertRaises(OpenDataError):
                fetch_source(source)
        self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 10)

    @patch("ttd_llm.open_data.urllib.request.build_opener")
    def test_oversize_network_response_refused(self, opener):
        source = SOURCES["nasa_eonet"]
        class Response:
            headers = {"Content-Type": "application/json"}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def geturl(self): return source.endpoint
            def read(self, size): return b"x" * size
        opener.return_value.open.return_value = Response()
        mock_stop = types.ModuleType("ai_killswitch")
        mock_stop.require_ai_allowed = lambda *_: None
        with patch.dict(sys.modules, {"ai_killswitch": mock_stop}):
            with self.assertRaises(OpenDataError):
                fetch_source(source)

    @patch("ttd_llm.open_data.main")
    def test_main_cli_forwards_open_data_command(self, main):
        from ttd_llm.__main__ import main as root_main
        main.return_value = 0
        self.assertEqual(root_main(["open-data", "sources"]), 0)
        main.assert_called_once_with(["sources"])


if __name__ == "__main__":
    unittest.main()
