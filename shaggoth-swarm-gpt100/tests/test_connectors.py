import unittest

from shaggoth_swarm.connectors import (
    AuthorizedConnectorMonitor,
    ConnectorConfig,
    _request_headers,
    _validate_endpoint,
)


class ConnectorTests(unittest.TestCase):
    def test_requires_explicit_endpoints(self):
        with self.assertRaises(ValueError):
            AuthorizedConnectorMonitor(ConnectorConfig(endpoints=()))

    def test_polls_only_configured_endpoints(self):
        seen = []

        def fake_probe(url, config, allowed):
            seen.append(url)
            self.assertIn(url, allowed)
            self.assertEqual(config.service_name, "shaggoth-swarm-gpt100")
            return {"endpoint": url, "ok": True}

        config = ConnectorConfig(
            endpoints=("https://example.com/health", "https://status.example.com/api"),
            interval_seconds=30,
        )
        monitor = AuthorizedConnectorMonitor(config, probe=fake_probe)
        events = monitor.poll_once()
        self.assertEqual(seen, list(config.endpoints))
        self.assertEqual(len(events), 2)

    def test_does_not_accept_arbitrary_nonlocal_http(self):
        with self.assertRaises(ValueError):
            _validate_endpoint("http://example.com/health")

        _validate_endpoint("http://127.0.0.1:8080/health")

    def test_uses_visible_service_identity_and_standard_auth(self):
        config = ConnectorConfig(
            endpoints=("https://example.com/health",),
            bearer_token="test-token",
        )
        headers = _request_headers(config)
        self.assertEqual(headers["User-Agent"], "shaggoth-swarm-gpt100/0.3.0")
        self.assertEqual(headers["X-Client-Service"], "shaggoth-swarm-gpt100")
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertTrue(headers["X-Request-ID"])

    def test_retry_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            ConnectorConfig(endpoints=("https://example.com/health",), max_retries=4)

        config = ConnectorConfig(endpoints=("https://example.com/health",), max_retries=3)
        self.assertEqual(config.max_retries, 3)

    def test_service_identity_cannot_contain_header_injection(self):
        with self.assertRaises(ValueError):
            ConnectorConfig(
                endpoints=("https://example.com/health",),
                service_name="fake-service\r\nX-Evil: 1",
            )


if __name__ == "__main__":
    unittest.main()
