"""Security and fixture tests for the XUNIA allowed-host crawler (no network)."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("xunia_authorized_crawl", ROOT / "scripts" / "xunia_authorized_crawl.py")
crawler = importlib.util.module_from_spec(spec)
sys.modules["xunia_authorized_crawl"] = crawler
spec.loader.exec_module(crawler)


class AuthorizedCrawlerTests(unittest.TestCase):
    def test_host_restrictions(self):
        for host in ["localhost", "service.local", "internal.internal", "hidden.onion", "127.0.0.1", "10.0.0.1", "::1"]:
            self.assertFalse(crawler.host_is_public(host), host)
        self.assertTrue(crawler.host_is_public("audit.example.org"))

    def test_only_explicit_exact_https_origin(self):
        h = "audit.example.org"
        self.assertTrue(crawler.allowed_url("https://audit.example.org/advisory", h))
        for candidate in [
            "http://audit.example.org/",
            "https://audit.example.org:8443/",
            "https://audit.example.org.evil.test/",
            "https://user:password@audit.example.org/",
            "https://127.0.0.1/private",
            "file:///etc/passwd",
            "https://audit.example.org@evil.org/",
        ]:
            self.assertFalse(crawler.allowed_url(candidate, h), candidate)

    def test_redirects_fail_closed_on_foreign_host(self):
        handler = crawler.RestrictedRedirect("audit.example.org")
        with self.assertRaises(ValueError):
            handler.redirect_request(
                Request("https://audit.example.org/"), None, 302, "redirect", {},
                "https://other.example.org/secret"
            )

    def test_robots_limits_scope_and_link_following(self):
        base = "https://audit.example.org/"
        html = b"""<html><title>Audit root</title>
        <a href="/allowed">Public</a><a href="/blocked">Blocked</a>
        <a href="https://bad.example.org/escape">External</a></html>"""
        responses = {
            base: (html, base),
            base + "allowed": (b"<title>Public next page</title>", base + "allowed")
        }
        with patch.object(crawler, "verified_addresses", return_value=True), \
             patch.object(crawler, "fetch_robots", return_value=(b"User-agent: *\nDisallow: /blocked\n", base + "robots.txt")), \
             patch.object(crawler, "fetch", side_effect=lambda url, host, timeout: responses[url]), \
             patch.object(crawler.time, "sleep", return_value=None):
            results = list(crawler.crawl(base, "audit.example.org", 3, 1, 3))
        self.assertEqual([r["url"] for r in results], [base, base + "allowed"])
        self.assertTrue(all(r["source"] == "authorized-site-audit" for r in results))

    def test_robots_error_is_not_bypassed(self):
        base = "https://audit.example.org/"
        with patch.object(crawler, "verified_addresses", return_value=True), \
             patch.object(crawler, "fetch_robots", side_effect=HTTPError(base, 403, "Forbidden", {}, None)):
            with self.assertRaisesRegex(ValueError, "robots.txt"):
                list(crawler.crawl(base, "audit.example.org", 3, 1, 3))

    def test_cli_requires_explicit_authorization(self):
        with self.assertRaises(SystemExit) as ctx:
            crawler.main(["--base-url", "https://audit.example.org/", "--allow-host", "audit.example.org"])
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
