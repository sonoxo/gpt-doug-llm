import unittest

from shaggoth_swarm.atomic import (
    ATOMIC_STACK,
    AtomicEnvelope,
    AtomicLayer,
    LayerSpec,
    stack_manifest,
    validate_stack,
    validate_transition,
)


class AtomicLayerTests(unittest.TestCase):
    def test_default_stack_is_valid_and_complete(self):
        valid, errors = validate_stack()
        self.assertTrue(valid, errors)
        self.assertEqual(len(ATOMIC_STACK), 8)
        self.assertEqual({spec.layer for spec in ATOMIC_STACK}, set(AtomicLayer))

    def test_governance_depends_on_all_lower_layers(self):
        governance = ATOMIC_STACK[-1]
        self.assertEqual(governance.layer, AtomicLayer.GOVERNANCE)
        self.assertEqual(
            set(governance.dependencies),
            set(AtomicLayer) - {AtomicLayer.GOVERNANCE},
        )

    def test_envelope_promotes_one_execution_layer_at_a_time(self):
        particle = AtomicEnvelope(kind="goal", payload={"goal": "build"})
        atom = particle.promote(AtomicLayer.ATOM, kind="capability-request")
        molecule = atom.promote(AtomicLayer.MOLECULE, kind="plan")
        self.assertEqual(atom.parent_id, particle.id)
        self.assertEqual(molecule.parent_id, atom.id)
        self.assertEqual(molecule.trace_id, particle.trace_id)

    def test_envelope_digest_is_stable_for_same_payload(self):
        left = AtomicEnvelope(kind="x", payload={"b": 2, "a": 1})
        right = AtomicEnvelope(kind="x", payload={"a": 1, "b": 2})
        self.assertEqual(left.digest, right.digest)

    def test_transition_cannot_skip_execution_layers(self):
        with self.assertRaises(ValueError):
            validate_transition(AtomicLayer.PARTICLE, AtomicLayer.CELL)

    def test_any_execution_layer_can_emit_governance_record(self):
        for layer in AtomicLayer:
            if layer is AtomicLayer.GOVERNANCE:
                continue
            validate_transition(layer, AtomicLayer.GOVERNANCE)

    def test_governance_cannot_reenter_execution_stack(self):
        with self.assertRaises(ValueError):
            validate_transition(AtomicLayer.GOVERNANCE, AtomicLayer.PARTICLE)

    def test_validation_rejects_non_lower_dependency(self):
        broken = list(ATOMIC_STACK)
        broken[1] = LayerSpec(
            layer=AtomicLayer.ATOM,
            name="atom",
            purpose="broken",
            dependencies=(AtomicLayer.CELL,),
            inputs=(),
            outputs=(),
            invariants=(),
        )
        valid, errors = validate_stack(broken)
        self.assertFalse(valid)
        self.assertTrue(any("non-lower" in error for error in errors))

    def test_manifest_is_serializable_shape(self):
        manifest = stack_manifest()
        self.assertTrue(manifest["valid"])
        self.assertEqual(manifest["layers"][0]["name"], "particle")
        self.assertEqual(manifest["layers"][-1]["name"], "governance")


if __name__ == "__main__":
    unittest.main()
