"""CL1-AURA local-browser smoke tests. No cloud, accounts or paid services."""
from __future__ import annotations

import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
import urllib.error
import urllib.request
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cl1_aura_web import AuraHandler, ASSETS


class LocalAuraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AuraHandler)
        cls.server.daemon_threads = True
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def get(self, path):
        req = urllib.request.Request("http://127.0.0.1:" + str(self.port) + path)
        with self.opener.open(req, timeout=3) as result:
            return result.status, result.headers, result.read()

    def test_local_pages_and_clickable_assets(self):
        for path in ("/", "/aura.js", "/style.css"):
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertTrue(body)
                self.assertIn("no-store", headers.get("Cache-Control", ""))
        html = self.get("/")[2].decode()
        self.assertIn('id="world"', html)
        self.assertIn('id="layers"', html)
        self.assertIn('src="/aura.js"', html)
        script = self.get("/aura.js")[2].decode()
        for text in ("pointerdown", "pointermove", "wheel", "selectNode", "renderInspector"):
            self.assertIn(text, script)

    def test_read_only_topology_api_never_exposes_bank_data(self):
        status, headers, payload = self.get("/api/topology")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("Content-Type", ""))
        graph = json.loads(payload)
        self.assertFalse(graph["external_calls"])
        self.assertFalse(graph["bank_accounts_connected"])
        self.assertFalse(graph["vault_unlocked"])
        self.assertGreater(len(graph["nodes"]), 10)
        self.assertTrue(all("details" in node for node in graph["nodes"]))
        self.assertTrue(all("short" in node for node in graph["nodes"]))
        self.assertNotIn("secret_key", payload.decode().lower())

    def test_telemetry_is_only_local_tcp_not_institutional_account_status(self):
        _, _, payload = self.get("/api/status")
        state = json.loads(payload)
        self.assertEqual(state["schema"], "cl1-aura/status-v1")
        self.assertIn("TCP", state["note"])
        self.assertFalse(state["bank_accounts_connected"])
        self.assertFalse(state["vault_unlocked"])
        self.assertEqual(state["health"]["bank"], "DENY")
        self.assertEqual(state["health"]["vault"], "SEALED")

    def test_untrusted_hosts_paths_and_post_are_denied(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            conn.request("GET", "/api/topology", headers={"Host": "evil.example"})
            r = conn.getresponse()
            self.assertEqual(r.status, 403)
            r.read()
            conn.request("POST", "/api/status", body=b"update",
                         headers={"Host": "127.0.0.1:" + str(self.port)})
            r = conn.getresponse()
            self.assertEqual(r.status, 405)
            r.read()
            conn.request("GET", "/../../web/crypto_store.py",
                         headers={"Host": "127.0.0.1:" + str(self.port)})
            r = conn.getresponse()
            self.assertEqual(r.status, 404)
            r.read()
        finally:
            conn.close()

    def test_static_files_remain_self_contained(self):
        js = (ASSETS / "aura.js").read_text(encoding="utf-8")
        self.assertIn('fetch("/api/status"', js)
        self.assertIn('fetch("/api/topology"', js)
        self.assertNotIn("https://", js)
        self.assertNotIn("api.openai.com", js)
        self.assertNotIn("bank_account", js)
        self.assertIn("pointerdown", js)


if __name__ == "__main__":
    unittest.main()
