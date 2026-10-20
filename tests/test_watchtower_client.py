import unittest
from universal_watchdog.client import GateDenied, WatchtowerClient, otel_observation


class ClientTests(unittest.TestCase):
    def test_insecure_remote_http_rejected(self):
        with self.assertRaises(ValueError):
            WatchtowerClient("t" * 32, "http://untrusted.invalid")

    def test_fail_closed_on_unavailable_gateway(self):
        cli = WatchtowerClient("t" * 32, "http://127.0.0.1:1")
        invoked = []
        with self.assertRaises(GateDenied):
            cli.execute({"model_id": "fake", "provider": "other"}, lambda: invoked.append('executed'))
        self.assertEqual(invoked, [])

    def test_otlp_span_translation_strips_content(self):
        obs = otel_observation({"gen_ai.system": "ollama", "gen_ai.request.model": "llama3:8b",
                                "gen_ai.usage.input_tokens": 10, "gen_ai.usage.output_tokens": 20,
                                "gen_ai.input.messages": "sensitive do not store"}, agent_id="observer")
        self.assertEqual(obs["estimated_tokens"], 30)
        self.assertEqual(obs["kind"], "telemetry")
        self.assertNotIn("sensitive", str(obs))


if __name__ == '__main__':
    unittest.main()
