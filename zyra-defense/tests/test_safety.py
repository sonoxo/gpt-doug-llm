import unittest

from zyra_ontology import (
    AuthorizationDecision,
    HumanAuthorization,
    HumanAuthority,
    Mission,
    OntologyStore,
    SafetyViolation,
    SimulatedTarget,
    Track,
    WeaponSystemModel,
    ZyraSimulationEngine,
)


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.store = OntologyStore()
        self.engine = ZyraSimulationEngine(self.store)
        self.mission = self.store.add(Mission(name="test"))
        self.track = self.store.add(Track(label="SIM", simulated=True))
        self.target = self.store.add(SimulatedTarget(track_id=self.track.id, label="sim"))

    def test_allows_advisory_simulation(self):
        model = self.store.add(WeaponSystemModel(name="abstract", has_actuation_interface=False))
        rec = self.engine.recommend_simulated_action(
            self.mission,
            self.target,
            self.track,
            "run synthetic effect model",
            "simulation-only",
            0.8,
            model,
        )
        self.assertTrue(rec.advisory_only)

    def test_blocks_real_world_actuation_language(self):
        with self.assertRaises(SafetyViolation):
            self.engine.recommend_simulated_action(
                self.mission,
                self.target,
                self.track,
                "fire",
                "real target",
                0.8,
            )

    def test_blocks_actuation_interface(self):
        model = self.store.add(
            WeaponSystemModel(name="unsafe", simulation_only=True, has_actuation_interface=True)
        )
        with self.assertRaises(SafetyViolation):
            self.engine.recommend_simulated_action(
                self.mission,
                self.target,
                self.track,
                "run synthetic effect model",
                "simulation-only",
                0.8,
                model,
            )

    def test_requires_human_approval(self):
        rec = self.engine.recommend_simulated_action(
            self.mission,
            self.target,
            self.track,
            "observe",
            "training",
            0.5,
        )
        req = self.engine.request_human_authorization(rec)
        authority = self.store.add(HumanAuthority(display_name="controller"))
        auth = self.store.add(
            HumanAuthorization(
                request_id=req.id,
                authority_id=authority.id,
                decision=AuthorizationDecision.DENY,
            )
        )
        with self.assertRaises(SafetyViolation):
            self.engine.simulate_effect(rec, auth, authority)


if __name__ == "__main__":
    unittest.main()
