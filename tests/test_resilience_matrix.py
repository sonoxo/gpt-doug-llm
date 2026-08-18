import copy
import tempfile
import unittest
from pathlib import Path

from resilience_matrix.engine import GameEngine, Ontology, ValidationError, load_default_ontology


class ResilienceMatrixTests(unittest.TestCase):
    def setUp(self):
        self.ontology = load_default_ontology()

    def test_ontology_validation_rejects_bad_reference(self):
        data = copy.deepcopy(self.ontology.data)
        scenarios = copy.deepcopy(self.ontology.scenarios)
        data["assets"][0]["owner"] = "S-DOES-NOT-EXIST"
        with self.assertRaises(ValidationError):
            Ontology(data, scenarios)

    def test_risk_update_changes_ordinal_state(self):
        engine = GameEngine(self.ontology, seed=17)
        target_index = engine.scenario_order.index("SC-CRYPTO")
        engine.turn = target_index
        before = engine.risk_view("R-CRYPTO")
        record = engine.decide("CRY-MIGRATE")
        after = engine.risk_view("R-CRYPTO")

        self.assertNotEqual(before["likelihood"], after["likelihood"])
        self.assertNotEqual(before["impact"], after["impact"])
        self.assertEqual(record["choice_id"], "CRY-MIGRATE")
        self.assertIn("ordinal", after["explanations"]["overall"])

    def test_save_load_round_trip(self):
        engine = GameEngine(self.ontology, seed=23)
        engine.decide("1")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            engine.save(path)
            restored = GameEngine(self.ontology, seed=999)
            restored.load(path)

        self.assertEqual(restored.seed, 23)
        self.assertEqual(restored.turn, engine.turn)
        self.assertEqual(restored.scenario_order, engine.scenario_order)
        self.assertEqual(restored.track_labels(), engine.track_labels())
        self.assertEqual(restored.history, engine.history)
        self.assertEqual(
            restored.risk_view("R-SUPPLIER")["overall"],
            engine.risk_view("R-SUPPLIER")["overall"],
        )

    def test_seeded_scenarios_are_deterministic(self):
        first = GameEngine(self.ontology, seed=101)
        second = GameEngine(self.ontology, seed=101)
        different = GameEngine(self.ontology, seed=102)

        self.assertEqual(first.scenario_order, second.scenario_order)
        self.assertNotEqual(first.scenario_order, different.scenario_order)
        self.assertEqual(len(first.scenario_order), 8)

    def test_dependency_map_is_readable(self):
        engine = GameEngine(self.ontology, seed=7)
        graph = engine.dependency_map()
        self.assertIn("ASCII DEPENDENCY GRAPH", graph)
        self.assertIn("--D-IDENTITY-REG:identity and authorization-->", graph)

    def test_eight_turns_end_with_executive_assessment(self):
        engine = GameEngine(self.ontology, seed=5)
        for _ in range(engine.MAX_TURNS):
            engine.decide("1")
        assessment = engine.executive_assessment()
        self.assertTrue(engine.finished)
        self.assertEqual(assessment["turns_completed"], 8)
        self.assertTrue(assessment["recommendations"])


if __name__ == "__main__":
    unittest.main()
