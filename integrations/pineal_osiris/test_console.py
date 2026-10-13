"""Loopback console HTTP/security contract tests (offline, no external feeds)."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from console import ConsoleServer


class ConsoleHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ConsoleServer(0, lambda: {
            "dashboard": {"serving": False},
            "map_url": "http://127.0.0.1:3000/",
            "pineal": {"state": "NOT_INITIALIZED", "feed_health_records": 0},
            "safe_routes": {},
        })
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def test_loopback_binding_and_explicit_host(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        url = f"http://127.0.0.1:{self.port}/api/status"
        with urlopen(url, timeout=3) as response:
            data = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertIn("no-store", response.headers["Cache-Control"])
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
            self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertEqual(data["pineal"]["feed_health_records"], 0)

    def test_refuse_foreign_host_even_on_loopback(self):
        req = Request(f"http://127.0.0.1:{self.port}/api/status", headers={"Host": "evil.example"})
        with self.assertRaises(HTTPError) as err:
            urlopen(req, timeout=3)
        self.assertEqual(err.exception.code, 403)

    def test_only_known_static_routes_are_available(self):
        for path in ("/", "/app.js", "/style.css"):
            with self.subTest(path=path):
                with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=3) as res:
                    self.assertEqual(res.status, 200)
                    self.assertTrue(res.read())
        for path in ("/etc/passwd", "/../private.env", "/missing"):
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as err:
                    urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=3)
                self.assertEqual(err.exception.code, 404)

    def test_json_failure_does_not_disclose_exception(self):
        self.server.status_provider = lambda: (_ for _ in ()).throw(ValueError("secret /tmp/path"))
        with self.assertRaises(HTTPError) as err:
            urlopen(f"http://127.0.0.1:{self.port}/api/status", timeout=3)
        self.assertEqual(err.exception.code, 503)
        self.assertNotIn("secret", err.exception.read().decode())


if __name__ == "__main__":
    unittest.main()
