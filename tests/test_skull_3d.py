"""Real HTTP tests of SKULL-LLM 3D interface without a running model."""
from __future__ import annotations

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

from skull_llm.server import make_handler, serve


class _FakeEngine:
    def __init__(self, *, depth, remember, on_progress):
        self.depth = depth
        self.remember = remember
        self.progress = on_progress

    def run(self, task):
        self.progress("retrieve", "Recalled local ontology")
        self.progress("draft", "Drafted a model response")
        if self.depth >= 2:
            self.progress("critique", "Checked assumptions")
            self.progress("revise", "Revised response")
        return SimpleNamespace(
            answer="Local response: " + task,
            calls=1 if self.depth == 1 else 3,
            provenance=["ontology:source"],
            warnings=[],
        )


class Local3DServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        status = lambda: {
            "ready_for_inference": False,
            "ollama": {"configured": False, "model_available": False},
            "stopped": False,
        }
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(engine_factory=_FakeEngine, status_fn=status)
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, *, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        headers = headers or {}
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        connection.close()
        return result

    def test_serves_real_3d_page_and_assets_without_remote_scripts(self):
        code, headers, page = self.request("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn(b'canvas id="brain-scene"', page)
        self.assertIn(b'/static/skull.js', page)
        self.assertIn(b'/static/fallback.js', page)
        self.assertNotIn(b'https://', page)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        for path in ("/static/skull.css", "/static/skull.js", "/static/fallback.js"):
            status, _, data = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertGreater(len(data), 500)

    def test_status_reports_inference_unavailable_without_pretending(self):
        code, _, body = self.request("GET", "/api/status")
        self.assertEqual(code, 200)
        self.assertFalse(json.loads(body)["ready_for_inference"])

    def test_3d_client_streams_real_reasoning_phases_and_final_result(self):
        payload = json.dumps({"task": "Build a neural graph", "depth": 2, "remember": False})
        code, headers, body = self.request(
            "POST", "/api/chat", body=payload,
            headers={"Content-Type": "application/json",
                     "Origin": f"http://127.0.0.1:{self.server.server_port}"},
        )
        self.assertEqual(code, 200)
        self.assertIn("application/x-ndjson", headers["Content-Type"])
        events = [json.loads(line) for line in body.splitlines()]
        self.assertEqual([event["type"] for event in events], [
            "phase", "phase", "phase", "phase", "answer"
        ])
        self.assertEqual(events[-1]["answer"], "Local response: Build a neural graph")
        self.assertEqual(events[-1]["calls"], 3)

    def test_rejects_invalid_origin_host_and_excessive_payload(self):
        payload = json.dumps({"task": "Safe task", "depth": 2})
        status, _, _ = self.request("POST", "/api/chat", body=payload, headers={
            "Content-Type": "application/json", "Origin": "https://attacker.example"
        })
        self.assertEqual(status, 403)
        code, _, _ = self.request("GET", "/api/status", headers={"Host": "untrusted.example"})
        self.assertEqual(code, 403)
        status, _, _ = self.request("POST", "/api/chat", body="x" * 17000,
                                    headers={"Content-Type": "application/json"})
        self.assertEqual(status, 413)
        code, _, _ = self.request("POST", "/api/chat", body=json.dumps({
            "task": "test", "depth": True
        }), headers={"Content-Type": "application/json"})
        self.assertEqual(code, 400)

    def test_only_allowlisted_paths(self):
        for path in ("/../pyproject.toml", "/static/../server.py", "/api/secrets"):
            code, _, _ = self.request("GET", path)
            self.assertEqual(code, 404)

    def test_loopback_only_listener(self):
        with self.assertRaises(ValueError):
            serve(host="0.0.0.0", port=7861)


if __name__ == "__main__":
    unittest.main()
