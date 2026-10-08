import unittest

from shaggoth_swarm.connectors import AuthorizedConnectorMonitor, ConnectorConfig


class ConnectorTests(unittest.TestCase):
    def test_requires_explicit_endpoints(self):
        with self.assertRaises(ValueError):
            AuthorizedConnectorMonitor(ConnectorConfig(endpoints=()))

    def test_polls_only_configured_endpoints(self):
        seen = []

        def fake_probe(url, timeout, max_bytes, allowed):
            seen.append(url)
            self.assertIn(url, allowed)
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
        from shaggoth_swarm.connectors import _validate_endpoint

        with self.assertRaises(ValueError):
            _validate_endpoint("http://example.com/health")

        _validate_endpoint("http://127.0.0.1:8080/health")


if __name__ == "__main__":
    unittest.main()
