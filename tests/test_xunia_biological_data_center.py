"""XUNIA Biological Data Center: zero-billing Pages + localhost telemetry tests."""
from __future__ import annotations

import http.client
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import socket
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "xunia_bio_cl1.py"
spec = importlib.util.spec_from_file_location("xunia_bio_cl1", SOURCE)
assert spec and spec.loader
bio = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bio
spec.loader.exec_module(bio)


class OntologyContractTests(unittest.TestCase):
    def setUp(self):
        self.doc = ROOT / "docs" / "biological-data-center"
        self.data = json.loads((self.doc / "ontology.json").read_text(encoding="utf-8"))

    def test_full_ontology_uses_referential_integrity_and_real_source_tags(self):
        self.assertTrue(bio.ontology_valid())
        self.assertEqual(self.data["schema"], "xunia.cl1.biological-data-center.v1")
        self.assertEqual(len(self.data["nodes"]), 30)
        self.assertEqual(len(self.data["edges"]), 43)
        ids = {n["id"] for n in self.data["nodes"]}
        self.assertEqual(len(ids), 30)
        self.assertTrue(all(e["from"] in ids and e["to"] in ids for e in self.data["edges"]))
        self.assertTrue(all(n["source_state"] in {"main","feature-branch","new-pr","concept"}
                            for n in self.data["nodes"]))
        for node_id in ("bio-core", "telemetry", "host"):
            node = next(n for n in self.data["nodes"] if n["id"] == node_id)
            self.assertEqual(node["source_state"], "main")
        self.assertEqual(self.data["public_hosting"], "GitHub Pages static docs")
        self.assertFalse(self.data["security"]["bank_accounts_connected"])
        self.assertFalse(self.data["security"]["biological_devices_connected"])
        self.assertFalse(self.data["security"]["paid_services"])

    def test_public_ui_is_self_contained_and_marks_simulation(self):
        html = (self.doc / "index.html").read_text(encoding="utf-8")
        js = (self.doc / "app.js").read_text(encoding="utf-8")
        css = (self.doc / "style.css").read_text(encoding="utf-8")
        for content in (html,js,css):
            self.assertNotIn("vercel", content.lower())
            self.assertNotIn("sk_live_", content)
        for name in ("world","layers","nodeTitle","genomeResults","telemetryMode"):
            self.assertIn(f'id="{name}"', html)
        self.assertIn("SYNTHETIC VISUAL PULSE", html)
        self.assertIn("BIOLOGICAL COMPUTE ARCHITECTURE // SOFTWARE MODEL", html)
        self.assertIn('fetch("./ontology.json"', js)
        self.assertIn('fetch("../ecosystem-observatory/snapshot.json"', js)
        self.assertIn('fetch("/api/telemetry"', js)
        self.assertIn("pointerdown",js)
        self.assertIn("pointermove",js)
        self.assertIn("wheel",js)
        self.assertIn("reduceMotion",js)
        self.assertIn("textContent",js)
        self.assertNotIn("innerHTML",js)
        self.assertIn("prefers-reduced-motion",css)

    def test_telemetry_only_probes_loopback_and_does_not_claim_hardware(self):
        calls = []
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): return False
        def connect(address, timeout):
            calls.append(address)
            return Connection()
        with patch.object(bio.socket,"create_connection",side_effect=connect):
            result = bio.telemetry_snapshot()
        self.assertEqual(result["source"], "127.0.0.1")
        self.assertFalse(result["public"])
        self.assertEqual(set(result["services"]), set(bio.PORTS))
        self.assertEqual(set(calls), {("127.0.0.1",port) for port in bio.PORTS.values()})
        self.assertTrue(all(v=="LISTENING" for v in result["services"].values()))
        self.assertFalse(result["biohardware_connected"])
        self.assertFalse(result["bank_accounts_connected"])
        self.assertFalse(result["vault_unlocked"])
        self.assertNotIn("hostname",result)
        self.assertNotIn("username",result)
        self.assertNotIn("openai",str(result).lower())

    def test_unavailable_loopback_service_is_offline(self):
        with patch.object(bio.socket,"create_connection",side_effect=ConnectionError("offline")):
            self.assertEqual(bio.probe_loopback(11434), "OFFLINE")
        self.assertEqual(bio.probe_loopback(0), "UNTESTED")


class LocalHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1",0),bio.BioHandler)
        cls.server.daemon_threads = True
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self,path,method="GET",headers=None,body=None):
        connection = http.client.HTTPConnection("127.0.0.1",self.port,timeout=4)
        try:
            custom={"Host":f"127.0.0.1:{self.port}"}
            if headers: custom.update(headers)
            connection.request(method,path,body=body,headers=custom)
            response=connection.getresponse()
            return response.status,response.headers,response.read()
        finally:
            connection.close()

    def test_site_and_json_are_served_only_from_allowlist(self):
        for path,mime in [
            ("/biological-data-center/","text/html"),
            ("/biological-data-center/app.js","text/javascript"),
            ("/biological-data-center/style.css","text/css"),
            ("/biological-data-center/ontology.json","application/json"),
            ("/ecosystem-observatory/snapshot.json","application/json"),
        ]:
            with self.subTest(path=path):
                code,headers,body=self.request(path)
                self.assertEqual(code,200)
                self.assertIn(mime,headers.get("Content-Type",""))
                self.assertIn("no-store",headers.get("Cache-Control",""))
                self.assertIn("default-src 'self'",headers.get("Content-Security-Policy",""))
                self.assertGreater(len(body),10)
        self.assertEqual(self.request("/")[0],302)
        self.assertEqual(self.request("/web/crypto_store.py")[0],404)
        self.assertEqual(self.request("/../../agents/glassonion_private_vault.py")[0],404)

    def test_local_vitals_schema_and_no_cors(self):
        code,headers,body=self.request("/api/telemetry")
        self.assertEqual(code,200)
        state=json.loads(body)
        self.assertEqual(state["schema"],"xunia.cl1.local-telemetry.v1")
        self.assertEqual(state["source"],"127.0.0.1")
        self.assertNotIn("Access-Control-Allow-Origin",dict(headers))
        self.assertEqual(state["confidence"],"TCP listening only; not application identity or biological hardware")

    def test_foreign_host_origin_and_cross_site_rejected(self):
        self.assertEqual(self.request("/api/telemetry",headers={"Host":"attacker.example"})[0],403)
        self.assertEqual(self.request("/api/telemetry",headers={"Origin":"https://attacker.example"})[0],403)
        self.assertEqual(self.request("/api/telemetry",headers={"Sec-Fetch-Site":"cross-site"})[0],403)

    def test_chatgpt_link_opens_local_site_without_cross_site_api_access(self):
        # Chrome reports a link from chatgpt.com as a cross-site navigation.
        # A browser may also append utm_source=chatgpt.com to the URL.
        navigation = {
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Referer": "https://chatgpt.com/",
        }
        status, headers, _ = self.request(
            "/?utm_source=chatgpt.com", headers=navigation
        )
        self.assertEqual(status, 302)
        self.assertEqual(headers.get("Location"), "/biological-data-center/")
        status, _, body = self.request(
            "/biological-data-center/", headers=navigation
        )
        self.assertEqual(status, 200)
        self.assertIn(b"BIOLOGICAL DATA CENTER", body)
        self.assertEqual(self.request(
            "/biological-data-center/index.html", headers=navigation
        )[0], 200)

        # Data and non-document paths remain inaccessible cross-site.
        for path in (
            "/api/telemetry",
            "/biological-data-center/ontology.json",
            "/biological-data-center/app.js",
            "/ecosystem-observatory/snapshot.json",
            "/",
        ):
            with self.subTest(path=path):
                # A cross-site subresource fetch is never a top-level nav.
                forged = {**navigation, "Sec-Fetch-Mode": "cors",
                          "Sec-Fetch-Dest": "empty"}
                self.assertEqual(self.request(path, headers=forged)[0], 403)
        self.assertEqual(
            self.request("/api/telemetry", headers=navigation)[0], 403,
        )
        self.assertEqual(
            self.request("/biological-data-center/app.js",
                         headers=navigation)[0], 403,
        )

    def test_foreign_origin_and_host_still_block_navigation(self):
        nav = {
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }
        self.assertEqual(self.request(
            "/?utm_source=chatgpt.com",
            headers={**nav, "Host": "attacker.example"},
        )[0], 403)
        self.assertEqual(self.request(
            "/?utm_source=chatgpt.com",
            headers={**nav, "Origin": "https://attacker.example"},
        )[0], 403)
        self.assertEqual(self.request(
            "/?utm_source=chatgpt.com",
            headers={**nav, "Sec-Fetch-Dest": "iframe"},
        )[0], 403)
        self.assertEqual(self.request(
            "/?utm_source=chatgpt.com",
            method="HEAD", headers=nav,
        )[0], 403)

    def test_no_network_mutation_methods(self):
        for method in ("POST","PUT","OPTIONS"):
            with self.subTest(method=method):
                code,_,_=self.request("/api/telemetry",method=method,body=b'{"activate":true}')
                self.assertEqual(code,405)
        code,_,body=self.request("/biological-data-center/app.js",method="HEAD")
        self.assertEqual(code,200)
        self.assertFalse(body)


if __name__ == "__main__":
    unittest.main()
