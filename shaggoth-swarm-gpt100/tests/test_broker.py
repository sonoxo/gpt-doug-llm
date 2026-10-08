import unittest

from shaggoth_swarm.broker import CapabilityBroker
from shaggoth_swarm.policy import CapabilityPolicy


class CapabilityBrokerTests(unittest.TestCase):
    def test_scoped_handler_runs_for_approved_resource(self):
        policy = CapabilityPolicy(allowed=frozenset({"github.write"}))
        policy.grant_scope("github.write", frozenset({"sonoxo/gpt-doug-llm"}))
        broker = CapabilityBroker(policy)
        broker.register("github.write", lambda value: f"wrote:{value}")

        result = broker.invoke(
            "github.write",
            "ok",
            scope="sonoxo/gpt-doug-llm",
        )
        self.assertEqual(result, "wrote:ok")

    def test_scoped_handler_is_blocked_without_scope(self):
        policy = CapabilityPolicy(allowed=frozenset({"github.write"}))
        broker = CapabilityBroker(policy)
        broker.register("github.write", lambda: "nope")

        with self.assertRaises(PermissionError):
            broker.invoke("github.write")

    def test_disabled_capability_is_blocked_even_if_handler_exists(self):
        policy = CapabilityPolicy()
        broker = CapabilityBroker(policy)
        broker.register("process.run", lambda: "nope")

        with self.assertRaises(PermissionError):
            broker.invoke("process.run", scope="/workspace")


if __name__ == "__main__":
    unittest.main()
