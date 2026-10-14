"""No-network, standard-library regression tests for the Universal Council."""
from __future__ import annotations

import math
import sys
import types
import unittest
from unittest.mock import patch

from agents.stark_ironman import Evidence
from agents.universal_council import (
    BoundedRSI, ImprovementCandidate, Metrics, UniversalCouncil, simulate_biochip,
)


class FakeNeuroGraph:
    def __init__(self, neurons):
        self.neurons = neurons
        self.state = [0.0] * neurons

    def tick(self, stimuli):
        self.state = [math.tanh(v + 0.2 * previous)
                      for v, previous in zip(stimuli, self.state)]
        return list(self.state)


class CouncilTests(unittest.TestCase):
    def council(self, **kwargs):
        return UniversalCouncil(graph_factory=FakeNeuroGraph, **kwargs)

    def test_all_six_roles_present(self):
        r = self.council().run("Build a source-controlled research prototype")
        self.assertEqual(len(r["agents"]), 6)
        self.assertIn("gpt-orca-llm", r["agents"])
        self.assertIn("gpt-doug-mlm", r["agents"])
        self.assertEqual(r["orca"]["status"], "opt_in_not_run")
        self.assertEqual(r["mlm"]["status"], "opt_in_not_run")
        self.assertEqual(r["stark"]["execution"], "not_executed")
        self.assertEqual(r["ironman"]["mode"], "dry_run")
        self.assertEqual(r["ironman"]["completed"], 0)
        self.assertFalse(r["permissions"]["automated_code_changes"])
        self.assertFalse(r["permissions"]["self_replication"])
        self.assertFalse(r["permissions"]["hardware_control"])

    def test_evidence_is_preserved_not_upgraded(self):
        evidence = [Evidence("registry-1", "trial status asserted by source", "https://example.org/trial")]
        report = self.council().run("Compare statuses", evidence=evidence)
        self.assertEqual(report["source_ids"], ["registry-1"])
        self.assertEqual(report["stark"]["evidence"][0]["provenance"], "https://example.org/trial")
        self.assertIn("No independent validation", report["stark"]["unknowns"][0])

    def test_empty_goal_and_overlength_rejected(self):
        for goal in ("", "   ", "X" * 4001):
            with self.subTest(goal_length=len(goal)), self.assertRaises(ValueError):
                self.council().run(goal)

    def test_duplicate_or_excessive_sources_rejected(self):
        dup = [Evidence("id", "a", "b"), Evidence("id", "c", "d")]
        with self.assertRaises(ValueError):
            self.council().run("Goal", evidence=dup)
        with self.assertRaises(ValueError):
            self.council().run("Goal", evidence=[Evidence(str(i), "a", "b") for i in range(17)])

    def test_biochip_deterministic_bounded_and_synthetic(self):
        x = simulate_biochip(goal="Synthetic biology study", neurons=16, cycles=4,
                             graph_factory=FakeNeuroGraph)
        y = simulate_biochip(goal="Synthetic biology study", neurons=16, cycles=4,
                             graph_factory=FakeNeuroGraph)
        self.assertEqual(x, y)
        self.assertEqual(len(x["final_state"]), 16)
        self.assertFalse(x["biological_hardware"])
        self.assertFalse(x["physical_actuation"])

    def test_unbounded_neuron_requests_rejected(self):
        for neurons, cycles in ((1, 1), (65, 1), (12, 0), (12, 9)):
            with self.subTest(neurons=neurons, cycles=cycles), self.assertRaises(ValueError):
                simulate_biochip(goal="test", neurons=neurons, cycles=cycles,
                                 graph_factory=FakeNeuroGraph)

    def test_backend_must_produce_finite_normalized_state(self):
        class BadGraph(FakeNeuroGraph):
            def tick(self, stimuli):
                return [float("nan")] * self.neurons
        with self.assertRaises(ValueError):
            simulate_biochip(goal="test", graph_factory=BadGraph)

    def test_no_provider_registry_prevents_named_reviewer(self):
        with self.assertRaises(ValueError):
            self.council().run("research", mlm_reviewers=["example"])

    def test_only_explicitly_registered_model_can_review(self):
        class Provider:
            def review(self, prompt):
                return "source-gated review"
        class Registry:
            def get(self, name):
                if name != "local":
                    raise KeyError(name)
                return Provider()
        r = self.council(provider_registry=Registry()).run("research", mlm_reviewers=["local"])
        self.assertEqual(r["mlm"]["reviews"][0]["text"], "source-gated review")
        self.assertFalse(r["mlm"]["reviews"][0]["verified"])

    def test_live_orca_api_is_explicitly_opt_in(self):
        class StubEvidence:
            def __init__(self, source_id, text, provenance):
                self.source_id = source_id
                self.text = text
                self.provenance = provenance
        class FakeOrca:
            def __init__(self, backend=None):
                self.backend = backend
            def run(self, task, evidence):
                return types.SimpleNamespace(completed=True, evidence_ids=[e.source_id for e in evidence],
                    turns=[types.SimpleNamespace(role="critic", output="proposal", error=None)],
                    answer="unverified proposal")
        with patch.dict(sys.modules, {
            "agents.gpt_orca_llm": types.SimpleNamespace(OrcaCouncil=FakeOrca),
            "agents.adaptive_intelligence": types.SimpleNamespace(Evidence=StubEvidence),
        }):
            r = self.council(orca_backend=lambda *a, **k: {}).run(
                "research", live_orca=True, evidence=[Evidence("s", "text", "public")])
        self.assertTrue(r["orca"]["model_called"])
        self.assertEqual(r["orca"]["status"], "completed")
        self.assertTrue(r["orca"]["outputs_are_unverified"])

    def test_cooperative_emergency_stop_is_respected(self):
        with patch("agents.universal_council.require_ai_allowed", side_effect=PermissionError("STOP")):
            with self.assertRaises(PermissionError):
                self.council().run("test")


class BoundedRSITests(unittest.TestCase):
    BASELINE = Metrics(0.5, 0.8, 0.5)

    def candidate(self, **changes):
        fields = dict(candidate_id="p1", description="Higher-quality validation",
            measured=Metrics(0.7, 0.85, 0.65), tests_passed=True,
            source_ids=("measurement",), evaluation_ref="measurement")
        fields.update(changes)
        return ImprovementCandidate(**fields)

    def assess(self, *rows, known=None):
        return BoundedRSI().evaluate(baseline=self.BASELINE,
            proposals=rows, known_source_ids=known if known is not None else {"measurement"})

    def test_improvements_only_eligible_for_review_not_applied(self):
        p = self.assess(self.candidate())
        self.assertEqual(p["candidates"][0]["status"], "eligible_for_human_review")
        self.assertGreater(p["candidates"][0]["measured_delta"], 0)
        self.assertFalse(p["auto_merge"])
        self.assertFalse(p["auto_mutation"])

    def test_unknown_source_blocks(self):
        p = self.assess(self.candidate(source_ids=("absent",)))
        self.assertIn("unverified_provenance", p["candidates"][0]["reasons"])

    def test_no_evaluation_evidence_blocks(self):
        p = self.assess(self.candidate(evaluation_ref=""))
        self.assertIn("missing_evaluation_evidence", p["candidates"][0]["reasons"])

    def test_unsafe_regression_blocks_even_with_quality_improvement(self):
        p = self.assess(self.candidate(measured=Metrics(1.0, 0.4, 1.0)))
        self.assertIn("safety_regression", p["candidates"][0]["reasons"])

    def test_failed_tests_block(self):
        p = self.assess(self.candidate(tests_passed=False))
        self.assertIn("tests_not_passing", p["candidates"][0]["reasons"])

    def test_permission_expansion_blocks(self):
        p = self.assess(self.candidate(permission_change=True))
        self.assertIn("permission_expansion_forbidden", p["candidates"][0]["reasons"])

    def test_no_gain_blocks(self):
        p = self.assess(self.candidate(measured=self.BASELINE))
        self.assertIn("no_measured_utility_gain", p["candidates"][0]["reasons"])

    def test_nan_and_out_of_range_metrics_rejected(self):
        for metrics in (Metrics(float("nan"), 0.5, 0.5), Metrics(2.0, 0.5, 0.5),
                        Metrics(float("inf"), 0.5, 0.5)):
            with self.subTest(metrics=metrics), self.assertRaises(ValueError):
                self.assess(self.candidate(measured=metrics))

    def test_duplicate_candidates_rejected(self):
        with self.assertRaises(ValueError):
            self.assess(self.candidate(), self.candidate())

    def test_maximum_candidate_limit(self):
        proposals = [self.candidate(candidate_id=str(i)) for i in range(9)]
        with self.assertRaises(ValueError):
            self.assess(*proposals)

    def test_no_proposals_no_mutation(self):
        r = self.assess()
        self.assertEqual(r["candidate_count"], 0)
        self.assertFalse(r["model_training"])


if __name__ == "__main__":
    unittest.main()

# Extended multi-round RSI checks deliberately run without any model or network.
class MultiRoundRSITests(unittest.TestCase):
    def setUp(self):
        self.lab = BoundedRSI()
        self.baseline = Metrics(0.5, 0.7, 0.5)
        self.rows = [ImprovementCandidate(
            candidate_id="a", description="Test candidate A",
            measured=Metrics(0.7, 0.75, 0.6), tests_passed=True,
            source_ids=("eval",), evaluation_ref="eval")]

    def test_two_rounds_never_promote_baseline_or_commit(self):
        second = ImprovementCandidate(candidate_id="b", description="Better measured validation",
            measured=Metrics(0.8, 0.8, 0.6), tests_passed=True,
            source_ids=("eval",), evaluation_ref="eval")
        result = self.lab.evaluate_rounds(baseline=self.baseline,
            rounds=[self.rows, [second]], known_source_ids={"eval"})
        self.assertEqual(result["round_count"], 2)
        self.assertEqual(result["top_candidate_for_review"], "b")
        self.assertTrue(result["baseline_unchanged"])
        self.assertFalse(result["auto_merge"])

    def test_round_count_bounded(self):
        with self.assertRaises(ValueError):
            self.lab.evaluate_rounds(baseline=self.baseline, rounds=[], known_source_ids={"eval"})
        with self.assertRaises(ValueError):
            self.lab.evaluate_rounds(baseline=self.baseline, rounds=[[], [], [], []],
                                     known_source_ids={"eval"})

    def test_duplicate_ids_across_rounds_denied(self):
        with self.assertRaises(ValueError):
            self.lab.evaluate_rounds(baseline=self.baseline,
                                     rounds=[self.rows, self.rows], known_source_ids={"eval"})