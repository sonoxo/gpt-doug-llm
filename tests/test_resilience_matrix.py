import copy
import json
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

    def test_scenario_control_must_be_mapped_to_risk(self):
        data = copy.deepcopy(self.ontology.data)
        scenarios = copy.deepcopy(self.ontology.scenarios)
        scenario = scenarios["scenarios"][0]
        risk = next(item for item in data["risks"] if item["id"] == scenario["risk_id"])
        unmapped = next(item["id"] for item in data["controls"] if item["id"] not in risk["controls"])
        scenario["choices"][0]["effects"]["control_id"] = unmapped
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
        self.assertEqual(restored.risk_view("R-SUPPLIER")["overall"], engine.risk_view("R-SUPPLIER")["overall"])

    def test_tampered_save_is_rejected_without_mutating_state(self):
        engine = GameEngine(self.ontology, seed=23)
        before = engine.status()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            engine.save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["tracks"]["readiness"] = 999
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                engine.load(path)
        self.assertEqual(engine.status(), before)

    def test_save_rejects_different_ontology_fingerprint(self):
        engine = GameEngine(self.ontology, seed=23)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            engine.save(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["ontology_fingerprint"] = "0" * 64
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                engine.load(path)

    def test_seeded_scenarios_are_deterministic(self):
        first = GameEngine(self.ontology, seed=101)
        second = GameEngine(self.ontology, seed=101)
        different = GameEngine(self.ontology, seed=102)
        self.assertEqual(first.scenario_order, second.scenario_order)
        self.assertNotEqual(first.scenario_order, different.scenario_order)
        self.assertEqual(len(first.scenario_order), 8)

    def test_dependency_map_is_readable(self):
        graph = GameEngine(self.ontology, seed=7).dependency_map()
        self.assertIn("ASCII DEPENDENCY GRAPH", graph)
        self.assertIn("--D-IDENTITY-REG:identity and authorization-->", graph)

    def test_status_reports_next_scenario(self):
        engine = GameEngine(self.ontology, seed=7)
        status = engine.status()
        self.assertEqual(status["turn"], 0)
        self.assertEqual(status["max_turns"], 8)
        self.assertEqual(status["next_scenario"], engine.scenario_order[0])

    def test_eight_turns_end_with_executive_assessment(self):
        engine = GameEngine(self.ontology, seed=5)
        for _ in range(engine.MAX_TURNS):
            engine.decide("1")
        assessment = engine.executive_assessment()
        self.assertTrue(engine.finished)
        self.assertEqual(assessment["turns_completed"], 8)
        self.assertTrue(assessment["recommendations"])
        self.assertEqual(len(assessment["priority_risks"]), 3)

    def test_ninth_decision_is_rejected(self):
        engine = GameEngine(self.ontology, seed=5)
        for _ in range(engine.MAX_TURNS):
            engine.decide("1")
        with self.assertRaises(RuntimeError):
            engine.decide("1")


if __name__ == "__main__":
    unittest.main()
