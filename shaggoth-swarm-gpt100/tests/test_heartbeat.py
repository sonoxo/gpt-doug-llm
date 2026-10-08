import unittest
from unittest.mock import patch

from shaggoth_swarm.heartbeat import build_heartbeat, format_heartbeat, probe_endpoint


class HeartbeatTests(unittest.TestCase):
    def test_build_heartbeat_reports_live_local_runtime(self):
        heartbeat = build_heartbeat()
        self.assertEqual(heartbeat.status, "alive")
        self.assertEqual(heartbeat.service, "shaggoth-swarm-gpt100")
        self.assertEqual(heartbeat.agent_capacity, 100)
        self.assertTrue(heartbeat.atomic_stack_valid)
        self.assertEqual(heartbeat.atomic_layer_count, 8)

    def test_format_heartbeat_is_single_line(self):
        line = format_heartbeat(build_heartbeat())
        self.assertIn("SHAGGOTH HEARTBEAT ALIVE", line)
        self.assertNotIn("\n", line)

    def test_failed_endpoint_marks_heartbeat_degraded(self):
        with patch(
            "shaggoth_swarm.heartbeat.probe_endpoint",
            return_value={"url": "http://127.0.0.1:8787/health", "ok": False},
        ):
            heartbeat = build_heartbeat("http://127.0.0.1:8787/health")
        self.assertEqual(heartbeat.status, "degraded")

    def test_endpoint_must_be_http_or_https(self):
        with self.assertRaises(ValueError):
            probe_endpoint("file:///tmp/x")


if __name__ == "__main__":
    unittest.main()
