import unittest

from shaggoth_swarm.atomic import AtomicEnvelope, AtomicLayer
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

    def test_atomic_invocation_promotes_particle_to_molecule(self):
        policy = CapabilityPolicy(allowed=frozenset({"reason"}))
        broker = CapabilityBroker(policy)
        broker.register("reason", lambda value: value.upper())
        particle = AtomicEnvelope(kind="goal", payload={"goal": "test"})

        molecule, result = broker.invoke_atomic(particle, "reason", "hello")

        self.assertEqual(result, "HELLO")
        self.assertEqual(molecule.layer, AtomicLayer.MOLECULE)
        self.assertEqual(molecule.trace_id, particle.trace_id)
        self.assertEqual(molecule.payload["capability"], "reason")

    def test_atomic_invocation_does_not_copy_arguments_or_results_into_envelope(self):
        secret = "sensitive-value"
        policy = CapabilityPolicy(allowed=frozenset({"reason"}))
        broker = CapabilityBroker(policy)
        broker.register("reason", lambda value: f"result:{value}")
        particle = AtomicEnvelope(kind="goal", payload={"goal": "test"})

        molecule, result = broker.invoke_atomic(particle, "reason", secret)

        self.assertIn(secret, result)
        self.assertNotIn(secret, repr(molecule.payload))
        self.assertNotIn(secret, molecule.digest)

    def test_atomic_invocation_rejects_non_atomic_entry_layer(self):
        policy = CapabilityPolicy(allowed=frozenset({"reason"}))
        broker = CapabilityBroker(policy)
        broker.register("reason", lambda: "ok")
        envelope = AtomicEnvelope(kind="x", payload={}).promote(AtomicLayer.ATOM)
        envelope = envelope.promote(AtomicLayer.MOLECULE)

        with self.assertRaises(ValueError):
            broker.invoke_atomic(envelope, "reason")


if __name__ == "__main__":
    unittest.main()
