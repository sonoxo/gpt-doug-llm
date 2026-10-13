"""Loopback-only GPT-Doug cognitive research console tests."""
from __future__ import annotations
from contextlib import contextmanager
import http.client
import json
import os
import threading
import unittest
from unittest import mock

from gpt_brain.cognitive_dashboard import HTML, build_server
from gpt_brain.evidence_fusion import build_demo_graph, main, verify_brief

@contextmanager
def dashboard():
    server = build_server(0, graph=build_demo_graph())
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

def get(server, path, host=None):
    port = server.server_address[1]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    headers = {"Host": host} if host is not None else {}
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()

class CognitiveDashboardTests(unittest.TestCase):
    def test_server_loopback_only(self):
        with dashboard() as server:
            self.assertEqual(server.server_address[0], "127.0.0.1")
    def test_page_renders_read_only_demo(self):
        with dashboard() as server:
            status, headers, body = get(server, "/")
            self.assertEqual(status, 200)
            self.assertIn(b"COGNITIVE LAB", body)
            self.assertIn(b"OFFLINE DEMO", body)
            self.assertIn(b"/api/brief", body)
            self.assertIn("nosniff", headers["X-Content-Type-Options"])
    def test_query_returns_verified_digest_not_source_authentication(self):
        with dashboard() as server:
            status, headers, body = get(server, "/api/brief?q=biopineal%20patent")
            report = json.loads(body)
            self.assertEqual(status, 200)
            self.assertTrue(verify_brief(report))
            self.assertFalse(report["workers"]["governance_auditor"]["source_authenticity_verified"])
            self.assertEqual(report["model_calls"], 0)
    def test_interactive_question_changes_evidence_selection(self):
        with dashboard() as server:
            a = json.loads(get(server, "/api/brief?q=patent")[2])
            b = json.loads(get(server, "/api/brief?q=synthetic%20heartbeat")[2])
            self.assertNotEqual(a["workers"]["evidence_curator"]["evidence"],
                                b["workers"]["evidence_curator"]["evidence"])
    def test_no_external_host_header(self):
        with dashboard() as server:
            status, _, body = get(server, "/", host="malicious.example")
            self.assertEqual(status, 403)
            self.assertNotIn(b"COGNITIVE LAB", body)
    def test_unknown_endpoint_returns_404(self):
        with dashboard() as server:
            self.assertEqual(get(server, "/private")[0], 404)
    def test_query_never_accepts_external_parameters(self):
        with dashboard() as server:
            self.assertEqual(get(server, "/api/brief?q=patent&remote=true")[0], 400)
    def test_empty_query_is_rejected(self):
        with dashboard() as server:
            self.assertEqual(get(server, "/api/brief?q=")[0], 400)
    def test_overlong_query_rejected(self):
        with dashboard() as server:
            self.assertEqual(get(server, "/api/brief?q=" + "a" * 600)[0], 400)
    def test_oversized_uri_rejected(self):
        with dashboard() as server:
            self.assertEqual(get(server, "/api/brief?q=" + "a" * 1600)[0], 414)
    def test_source_data_is_not_html_injected(self):
        self.assertIn("textContent", HTML)
        self.assertNotIn("innerHTML", HTML)
        self.assertNotIn("<iframe", HTML)
        self.assertNotIn("<script src=", HTML)
    def test_security_headers_exist(self):
        with dashboard() as server:
            status, headers, _ = get(server, "/api/brief?q=patent")
            self.assertEqual(status, 200)
            self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Frame-Options"], "DENY")
            self.assertEqual(headers["Cache-Control"], "no-store")
    def test_status_responds_offline_when_no_models(self):
        with dashboard() as server:
            result = json.loads(get(server, "/api/brief?q=patent")[2])
            self.assertTrue(result["read_only"])
            self.assertTrue(result["no_network"])
            self.assertEqual(result["external_actions"], 0)
    def test_stop_works_after_server_start(self):
        with dashboard() as server:
            with mock.patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
                code, _, body = get(server, "/api/brief?q=patent")
                self.assertIn(code, {400, 503})
                self.assertNotIn(b"workers", body)
    def test_invalid_port_rejected(self):
        with self.assertRaises(ValueError):
            build_server(99999)
    def test_cli_launch_option_dispatches(self):
        with mock.patch("gpt_brain.cognitive_dashboard.serve_demo") as start:
            self.assertEqual(main(["live-demo", "--port", "8867"]), 0)
            start.assert_called_once_with(8867)

if __name__ == "__main__":
    unittest.main()
