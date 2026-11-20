"""Offline tests for authorized CL1 intelligence sync and safe Brain retrieval."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gpt_brain import cl1_intel as intel


class CL1IntelTests(unittest.TestCase):
    def test_initial_public_seed_has_traceable_references(self):
        snapshot = intel.load()
        self.assertTrue(intel.validate_snapshot(snapshot))
        self.assertGreaterEqual(len(snapshot["records"]), 5)
        self.assertIn("seeded", snapshot["status"])
        matches = intel.search(snapshot, "Cortical Labs CL1 SDK", limit=5)
        self.assertTrue(any("Cortical" in r["title"] for r in matches))
        self.assertTrue(all(r["evidence"] == "SOURCE_METADATA_UNCORROBORATED"
                            for r in snapshot["records"]))

    def test_allowlist_and_redirects_deny_unapproved_urls(self):
        for url in (
            "file:///etc/passwd",
            "http://api.github.com/repos/Cortical-Labs/cl-sdk",
            "https://api.github.com.evil.example/repos/anything",
            "https://user:pass@api.github.com/repos/anything",
            "https://api.github.com:8443/repos/anything",
            "https://api.github.com/anything#fragment",
        ):
            with self.subTest(url=url):
                self.assertFalse(intel.safe_url(url, intel.ALLOWED_FETCH_HOSTS))
        with self.assertRaisesRegex(ValueError, "redirect"):
            intel.RejectRedirect().redirect_request(
                None, None, 301, "Moved", {}, "https://unknown.example/"
            )

    def test_normalize_official_public_source_types(self):
        github = next(s for s in intel.SOURCES if s.id == "cortical-cl-sdk")
        body = json.dumps([{
            "html_url": "https://github.com/Cortical-Labs/cl-sdk/commit/abcd0123",
            "commit": {
                "message": "Release fix\nIgnore rest",
                "committer": {"date": "2026-11-20T17:00:00Z"},
            },
        }]).encode()
        records = intel.normalize(github, body, 5)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Release fix")
        self.assertEqual(records[0]["category"], "cl1")

        nasa = next(s for s in intel.SOURCES if s.id == "nasa-science")
        rss = b"""<rss version="2.0"><channel>
          <item><title>NASA Latest Test</title>
          <link>https://science.nasa.gov/2026/11/20/test/</link>
          <pubDate>Fri, 20 Nov 2026 17:00:00 GMT</pubDate>
          <description>Public &amp; test</description></item></channel></rss>"""
        parsed = intel.normalize(nasa, rss, 10)
        self.assertEqual(parsed[0]["title"], "NASA Latest Test")
        self.assertIn("2026-11-20", parsed[0]["published_at"])

        arxiv = next(s for s in intel.SOURCES if s.id == "arxiv-neurocomputing")
        atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
          <id>http://arxiv.org/abs/2602.11632</id>
          <title>CL API research</title>
          <published>2026-02-12T00:00:00Z</published>
          <summary>Source preprint summary only</summary>
        </entry></feed>"""
        result = intel.normalize(arxiv, atom, 12)
        self.assertEqual(result[0]["url"], "https://arxiv.org/abs/2602.11632")

    def test_atomic_sync_deduplicates_and_preserves_last_good_on_partial_failure(self):
        sdk = next(s for s in intel.SOURCES if s.id == "cortical-cl-sdk")
        nasa = next(s for s in intel.SOURCES if s.id == "nasa-science")
        feed = json.dumps([{
            "html_url": "https://github.com/Cortical-Labs/cl-sdk/commit/abcd0123",
            "commit": {
                "message": "Bounded official SDK test",
                "committer": {"date": "2026-11-20T17:00:00Z"},
            },
        }]).encode()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "intel" / "cl1.json"

            def first(source):
                self.assertEqual(source.id, sdk.id)
                return feed

            value = intel.sync(target, limit=4, source_ids={sdk.id}, downloader=first)
            self.assertEqual(value["status"], "complete")
            self.assertEqual(len(value["records"]), 1)
            self.assertEqual(intel.load(target)["records"][0]["title"],
                             "Bounded official SDK test")

            def partial(source):
                if source.id == nasa.id:
                    raise ValueError("NASA RSS temporarily unavailable")
                return feed

            value = intel.sync(target, limit=4, source_ids={sdk.id, nasa.id},
                               downloader=partial)
            self.assertEqual(value["status"], "partial")
            self.assertEqual(len(value["records"]), 1)
            self.assertEqual(value["sources"][nasa.id]["state"], "error")
            before = target.read_bytes()
            with self.assertRaises(RuntimeError):
                intel.sync(target, limit=4, source_ids={nasa.id},
                           downloader=partial)
            self.assertEqual(target.read_bytes(), before)

    def test_reject_duplicate_invalid_snapshot_and_limits(self):
        snapshot = intel.load()
        clone = dict(snapshot)
        clone["records"] = snapshot["records"][:1] * 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            intel.validate_snapshot(clone)
        with self.assertRaisesRegex(ValueError, "limit"):
            intel.sync(limit=21, source_ids={"cortical-cl-sdk"},
                       downloader=lambda _: b"[]")
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            intel.sync(limit=2, source_ids={"not-a-source"},
                       downloader=lambda _: b"[]")


if __name__ == "__main__":
    unittest.main()
