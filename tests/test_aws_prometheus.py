"""Offline checks for the free-first Prometheus / optional AWS bridge."""
from __future__ import annotations

import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path

from observability.prometheus_aws.configure import configure, prometheus_config
from observability.prometheus_aws.metrics import GatewayMetrics


class PrometheusAWSBridgeTests(unittest.TestCase):
    def test_uptime_metric(self):
        metrics = GatewayMetrics()
        self.assertIn("gpt_doug_api_uptime_seconds", metrics.render())

    def test_request_count(self):
        metrics = GatewayMetrics()
        metrics.observe("GET", "/health", 200, .125)
        metrics.observe("GET", "/health", 200, .2)
        sample = metrics.render()
        self.assertIn('gpt_doug_api_requests_total{method="GET",route="/health",status="200"} 2', sample)
        self.assertIn('gpt_doug_api_request_duration_seconds_sum{method="GET",route="/health",status="200"} 0.325000', sample)

    def test_user_inputs_never_become_metric_labels(self):
        metrics = GatewayMetrics()
        metrics.observe("GET", '/someone/private?email=secret@example.com', 200, 0.1)
        metrics.observe("PATCH", '/inspect', 999, -1.0)
        sample = metrics.render()
        self.assertNotIn('email', sample)
        self.assertNotIn('secret', sample)
        self.assertNotIn('someone', sample)
        self.assertIn('route="other"', sample)
        self.assertIn('method="OTHER"', sample)
        self.assertIn('status="other"', sample)

    def test_thread_safety(self):
        metrics = GatewayMetrics()
        threads = [threading.Thread(target=lambda: [metrics.observe("POST", "/inspect", 200, 0.01) for _ in range(1000)]) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertIn('status="200"} 8000', metrics.render())

    def test_local_default_never_has_remote_write(self):
        config = prometheus_config()
        self.assertNotIn("remote_write", config)
        self.assertNotIn("amazonaws.com", config)
        self.assertIn("credentials_file: /etc/prometheus/metrics_token", config)
        self.assertIn("scrape_interval: 60s", config)

    def test_region_workspace_must_pair(self):
        with self.assertRaises(ValueError):
            prometheus_config(region="us-east-1")
        with self.assertRaises(ValueError):
            prometheus_config(workspace="ws-12345678-1234-1234-1234-123456789012")

    def test_invalid_aws_inputs_rejected(self):
        examples = [("bad region", "ws-12345678-1234-1234-1234-123456789012"),
                    ("us-east-1", "bad"),
                    ("us-east-1\nmalicious: true", "ws-12345678-1234-1234-1234-123456789012"),
                    ("us-east-1", "ws-12345678-1234-1234-1234-123456789012\nremote_write:")]
        for region, workspace in examples:
            with self.subTest(region=region, workspace=workspace):
                with self.assertRaises(ValueError):
                    prometheus_config(region=region, workspace=workspace)

    def test_amp_config_uses_sigv4_and_cost_relabel(self):
        config = prometheus_config("us-east-1", "ws-12345678-1234-1234-1234-123456789012")
        self.assertIn("remote_write:", config)
        self.assertIn("sigv4:", config)
        self.assertIn("region: us-east-1", config)
        self.assertIn("aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-12345678-1234-1234-1234-123456789012", config)
        self.assertIn("regex: 'gpt_doug_.*'", config)
        self.assertNotIn("access_key:", config)
        self.assertNotIn("secret_key:", config)

    def test_amp_requires_explicit_cost_acknowledgment_and_no_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime"
            with self.assertRaises(ValueError):
                configure(runtime, region="us-east-1",
                          workspace="ws-12345678-1234-1234-1234-123456789012")
            self.assertFalse(runtime.exists())

    def test_secret_persisted_on_reconfigure(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime"
            local = configure(runtime)
            self.assertEqual(local["mode"], "local_only")
            token = (runtime / "metrics_token").read_text()
            self.assertGreater(len(token), 45)
            self.assertFalse("remote_write" in (runtime / "prometheus.yml").read_text())
            configure(runtime, region="us-east-1",
                      workspace="ws-12345678-1234-1234-1234-123456789012",
                      billing_acknowledged=True)
            self.assertIn("remote_write", (runtime / "prometheus.yml").read_text())
            self.assertEqual((runtime / "metrics_token").read_text(), token)
            configure(runtime)
            self.assertNotIn("remote_write", (runtime / "prometheus.yml").read_text())
            self.assertEqual((runtime / "metrics_token").read_text(), token)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(runtime.stat().st_mode), 0o700)

    def test_bad_or_empty_token_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime"
            configure(runtime)
            (runtime / "metrics_token").write_text("")
            with self.assertRaises(ValueError):
                configure(runtime)

    def test_metric_endpoint_uses_authentication(self):
        """Smoke test the actual gateway without launching external services."""
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        from api_gateway.server import APIHandler

        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp)
            token_path = runtime / "token"
            token_path.write_text("correcttesttokencorrecttesttokencorrecttesttoken")
            with patch.dict(os.environ, {"GPT_DOUG_METRICS_TOKEN_FILE": str(token_path)}):
                server = ThreadingHTTPServer(("127.0.0.1", 0), APIHandler)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/metrics"
                    with self.assertRaises(HTTPError) as bad:
                        urlopen(url, timeout=2)
                    self.assertEqual(bad.exception.code, 401)
                    req = Request(url, headers={"Authorization": "Bearer correcttesttokencorrecttesttokencorrecttesttoken"})
                    with urlopen(req, timeout=2) as response:
                        self.assertEqual(response.status, 200)
                        result = response.read().decode("utf-8")
                    self.assertIn("gpt_doug_api_uptime_seconds", result)
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
