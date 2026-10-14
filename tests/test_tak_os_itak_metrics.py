"""Explicit private TAK metrics contract. Never contacts real TAK infrastructure."""
import importlib.util
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / "docs" / "tak-os"
spec = importlib.util.spec_from_file_location("private_tak_metrics", BASE / "itak_metrics.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def config():
    return {
        "TAK_METRICS_BASE_URL": "https://tak-authorized.test:8443",
        "TAK_METRICS_CLIENT_CERT": "/only/private/client.pem",
        "TAK_METRICS_CLIENT_KEY": "/only/private/client.key",
        "TAK_METRICS_CA_CERT": "/only/private/ca.pem",
        "TAK_METRICS_VIEW_TOKEN": "read-only-private-view-token-for-tests-00001",
    }


class PrivateMetricsUnitTests(unittest.TestCase):
    def test_unconfigured_and_bad_config_fail_closed(self):
        p = module.PrivateItakMetrics(env={})
        self.assertFalse(p.configured())
        self.assertEqual(p.sample(), (503, {"status": "not_configured", "metrics": None}))
        for url in ("http://example.org:8443", "https://example.org", "https://u:p@example.org:8443",
                    "https://example.org:8443/actuator", "https://example.org:8443/?a=1",
                    "https://example.org:99999"):
            env = config()
            env["TAK_METRICS_BASE_URL"] = url
            with self.subTest(url=url):
                self.assertFalse(module.PrivateItakMetrics(env=env).configured())
        env = config()
        env["TAK_METRICS_VIEW_TOKEN"] = "too-short"
        self.assertFalse(module.PrivateItakMetrics(env=env).configured())

    def test_admin_viewer_auth_is_separate_from_lab_session(self):
        p = module.PrivateItakMetrics(env=config(), transport=lambda _: None)
        self.assertTrue(p.configured())
        self.assertFalse(p.authorized(""))
        self.assertFalse(p.authorized("Bearer laboratory-session-token"))
        self.assertFalse(p.authorized("Basic dGVzdA=="))
        self.assertTrue(p.authorized("Bearer " + config()["TAK_METRICS_VIEW_TOKEN"]))
        self.assertNotIn("TAK_METRICS_VIEW_TOKEN", json.dumps(p.capabilities()))
        self.assertNotIn("tak-authorized.test", json.dumps(p.capabilities()))

    def test_aggregate_schema_sanitizes_sensitive_server_fields(self):
        raw = dict(numClients=7, bytesRead=12300, bytesWritten=22400, numReads=85,
                   numWrites=140, uid="secret-uid", callsign="SENSITIVE",
                   latitude=12.5, longitude=77.1, clientCertificates=["sensitive"])
        current = [10.0]
        p = module.PrivateItakMetrics(env=config(), transport=lambda _: raw,
                monotonic=lambda: current[0], wall_clock=lambda: "2026-10-14T00:00:00Z")
        status, report = p.sample()
        self.assertEqual(status, 200)
        self.assertEqual(report["metrics"]["numClients"], 7)
        self.assertIsNone(report["itakClients"])
        self.assertIsNone(report["rates"]["readsPerSecond"])
        self.assertNotIn("secret-uid", json.dumps(report))
        self.assertNotIn("SENSITIVE", json.dumps(report))
        self.assertNotIn("clientCertificates", json.dumps(report))
        current[0] = 11.5
        _, cached = p.sample()
        self.assertEqual(cached["sampleAgeSeconds"], 1.5)
        self.assertIsNone(cached["itakClients"])
        current[0] = 20.0
        raw["numReads"] += 40
        raw["bytesRead"] += 5000
        _, next_report = p.sample()
        self.assertEqual(next_report["rates"]["readsPerSecond"], 4.0)
        self.assertEqual(next_report["rates"]["bytesReceivedPerSecond"], 500.0)
        self.assertIsNone(next_report["itakDeviceBattery"])

    def test_failed_retrieval_and_counter_reversal_do_not_fabricate(self):
        raw = dict(numClients=1, bytesRead=5000, bytesWritten=4000, numReads=100, numWrites=100)
        now = [20.0]
        fail = [False]
        def source(_):
            if fail[0]:
                raise OSError("secret-host private-server/cert/path")
            return raw
        p = module.PrivateItakMetrics(env=config(), transport=source, monotonic=lambda: now[0])
        self.assertEqual(p.sample()[0], 200)
        now[0] = 30.0
        raw["numReads"] = 80
        self.assertIsNone(p.sample()[1]["rates"]["readsPerSecond"])
        now[0] = 40.0
        fail[0] = True
        code, response = p.sample()
        self.assertEqual(code, 502)
        self.assertIsNone(response["metrics"])
        self.assertNotIn("secret-host", json.dumps(response))
        self.assertEqual(p.sample()[0], 502)

    def test_reject_malformed_values(self):
        good = dict(numClients=1, bytesRead=1, bytesWritten=1, numReads=1, numWrites=1)
        for x in (None, -1, "3", True, 1.0, 1.4, float("inf"), 1e40):
            row = dict(good)
            row["numClients"] = x
            with self.subTest(value=x):
                with self.assertRaises(module.MetricsSourceError):
                    module.decode_network_metrics(row)
        self.assertEqual(module.decode_network_metrics(good)["numClients"], 1)


class MetricsRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location("itak_tak_os_gateway", BASE / "gateway.py")
        cls.gateway = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gateway)
        with patch.dict(os.environ, {}, clear=True):
            cls.server, cls.state = cls.gateway.build_server(port=0)
        cls.port = cls.server.server_port
        cls.root = "http://127.0.0.1:" + str(cls.port)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.state.stopped.set()
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=3)
        cls.state.close()

    def test_unconfigured_capabilities_have_no_operational_data(self):
        with urllib.request.urlopen(self.root + "/api/v1/itak/capabilities", timeout=3) as reply:
            obj = json.load(reply)
            self.assertEqual(reply.status, 200)
            self.assertEqual(reply.headers["Cache-Control"], "no-store")
        self.assertFalse(obj["configured"])
        self.assertFalse(obj["itakClientCountSupported"])
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(self.root + "/api/v1/itak/metrics", timeout=3)
        self.assertEqual(e.exception.code, 503)

    def test_live_route_requires_distinct_bearer_token_even_with_lab_token(self):
        current = [100.0]
        row = dict(numClients=2, bytesRead=123, bytesWritten=456, numReads=7, numWrites=8)
        self.state.itak_metrics = module.PrivateItakMetrics(
            env=config(), transport=lambda _: row, monotonic=lambda: current[0]
        )
        try:
            headers = {"Authorization": "Bearer " + self.state.token}
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(urllib.request.Request(
                    self.root + "/api/v1/itak/metrics", headers=headers), timeout=3)
            self.assertEqual(e.exception.code, 401)
            headers["Authorization"] = "Bearer " + config()["TAK_METRICS_VIEW_TOKEN"]
            req = urllib.request.Request(self.root + "/api/v1/itak/metrics", headers=headers)
            with urllib.request.urlopen(req, timeout=3) as response:
                payload = json.load(response)
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(payload["metrics"]["numClients"], 2)
            self.assertIsNone(payload["itakClients"])
            self.assertNotIn("tak-authorized.test", json.dumps(payload))
            self.assertNotIn("read-only-private-view-token", json.dumps(payload))
            with self.assertRaises(urllib.error.HTTPError) as rebinding:
                urllib.request.urlopen(urllib.request.Request(
                    self.root + "/api/v1/itak/metrics",
                    headers={**headers, "Host": "malicious.example"}), timeout=3)
            self.assertEqual(rebinding.exception.code, 403)
        finally:
            self.state.itak_metrics = module.PrivateItakMetrics(env={})


if __name__ == "__main__":
    unittest.main()
