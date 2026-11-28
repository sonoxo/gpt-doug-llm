"""Regression suite for simulator-only CL1 RSI, trusted evaluator and promotion gates."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agents.cl1_rsi_policy import decode_activity
from rsi_supervisor import (
    CL1_POLICY_PATH,
    ExternalBenchmark,
    Metrics,
    RecursiveImprovement,
    reject_unreviewed_scope,
)
from scripts.cl1_rsi_heldout import benchmark, balanced_accuracy, make_case
from scripts.prepare_cl1_rsi_evaluator import install

ROOT = Path(__file__).resolve().parents[1]


class MockAgent:
    def __init__(self, touched=CL1_POLICY_PATH, ok=True):
        self.touched = touched
        self.ok = ok
        self.goals = []
        self.rolled_back = []

    def run(self, objective, *, evolve=False):
        self.goals.append(objective)
        if not evolve:
            raise AssertionError("RSI must be an evolve mission")
        return SimpleNamespace(
            mission_id=f"m{len(self.goals)}",
            status="PASS", rolled_back=False,
            touched_files=[self.touched],
            checks=[{"check": "syntax", "ok": True}],
        )

    def rollback(self, mission_id):
        self.rolled_back.append(mission_id)
        return {"rolled_back": True}

    def _tool_run_check(self, name, paths):
        return {"check": name, "ok": self.ok}

    def _run_process(self, args, *, timeout):
        return {"ok": self.ok}


class Cl1RsiTests(unittest.TestCase):
    def test_synthetic_decoder_is_bounded_and_does_not_require_cl_sdk(self):
        self.assertEqual(decode_activity([], 5.0), [])
        self.assertEqual(decode_activity([1, 10, 7], 5.0), [0, 1, 1])
        for values, baseline in (
            ([2.0], 0), ([-1.0], 5), ([float("nan")], 5), ([0] * 1025, 5),
        ):
            with self.subTest(values=len(values)), self.assertRaises(ValueError):
                decode_activity(values, baseline)

    def test_heldout_synthetic_events_are_reproducible(self):
        self.assertEqual(make_case(113, 2), make_case(113, 2))
        rates, labels, baseline = make_case(113, 2)
        self.assertEqual(len(rates), 256)
        self.assertTrue(0 < sum(labels) < len(labels))
        self.assertTrue(0.0 <= balanced_accuracy(decode_activity(rates, baseline), labels) <= 1.0)

    def test_actual_heldout_evaluator_produces_non_regressing_strict_evidence(self):
        metrics = Metrics.from_json(benchmark(ROOT))
        self.assertGreater(metrics.quality, 0.65)
        self.assertEqual(metrics.regressions, 0)
        self.assertTrue(metrics.security_ok)

    def test_external_installed_evaluator_is_pinned_and_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trusted" / "cl1-heldout.py"
            info = install(path)
            self.assertEqual(info["status"], "INSTALLED")
            self.assertEqual(install(path)["status"], "UNCHANGED")
            external = ExternalBenchmark(path, ROOT, timeout=20)
            score = external()
            self.assertTrue(score.security_ok)
            self.assertGreater(score.quality, 0.65)
            path.write_text(path.read_text(encoding="utf-8") + "\n# tamper\n")
            with self.assertRaisesRegex(ValueError, "changed during the cycle"):
                external()
            with self.assertRaisesRegex(ValueError, "explicit --replace"):
                install(path)
            self.assertEqual(install(path, replace=True)["status"], "INSTALLED")

    def test_evaluator_installation_refuses_editable_repository(self):
        with self.assertRaises(ValueError):
            install(ROOT / "local-test-evaluator.py")

    def test_cl1_profile_requires_repeated_independent_measurements(self):
        with self.assertRaisesRegex(ValueError, "independent evaluator"):
            RecursiveImprovement(MockAgent(), profile="cl1-sim")
        with self.assertRaisesRegex(ValueError, "at least 3"):
            RecursiveImprovement(MockAgent(), profile="cl1-sim", benchmark=lambda: Metrics(.9, 0, True))
        with self.assertRaises(ValueError):
            RecursiveImprovement(MockAgent(), samples=6)

    def test_cl1_measured_gain_is_repeatable_and_requires_review(self):
        agent = MockAgent()
        evidence = iter(
            [Metrics(.78, 0, True)] * 3 + [Metrics(.82, 0, True)] * 3
        )
        supervisor = RecursiveImprovement(
            agent, profile="cl1-sim", samples=3,
            benchmark=lambda: next(evidence), min_gain=.01
        )
        report = supervisor.run("Reduce synthetic activity decoding errors")
        self.assertEqual(report["status"], "MEASURED_GAIN_REVIEW_REQUIRED")
        self.assertEqual(report["benchmark_samples"], 3)
        self.assertEqual(len(report["baseline_samples"]), 3)
        self.assertEqual(len(report["cycles"][0]["candidate_samples"]), 3)
        self.assertIn("synthetic CL1", agent.goals[0])
        self.assertEqual(agent.rolled_back, [])

    def test_cl1_profile_rejects_change_to_unrelated_or_protected_code(self):
        for path in ("agents/other.py", "tests/test_rsi_supervisor.py", "ai_killswitch.py"):
            with self.subTest(path=path):
                agent = MockAgent(touched=path)
                report = RecursiveImprovement(
                    agent, profile="cl1-sim", samples=3,
                    benchmark=lambda: Metrics(.8, 0, True),
                ).run("Improve synthetic decoder")
                self.assertEqual(report["cycles"][0]["decision"], "REJECT_PROTECTED_SCOPE")
                self.assertEqual(report["status"], "BLOCKED")
                self.assertEqual(agent.rolled_back, ["m1"])

    def test_baseline_regressions_block_mutations_before_agent_runs(self):
        agent = MockAgent()
        supervisor = RecursiveImprovement(
            agent, profile="cl1-sim", samples=3,
            benchmark=lambda: Metrics(.8, 1, False)
        )
        with self.assertRaisesRegex(ValueError, "baseline benchmark failed"):
            supervisor.run("Improve")
        self.assertEqual(agent.goals, [])

    def test_noisy_benchmark_cannot_claim_gain_or_touch_files(self):
        agent = MockAgent()
        seq = iter([Metrics(.70, 0, True), Metrics(.73, 0, True), Metrics(.72, 0, True)])
        supervisor = RecursiveImprovement(
            agent, profile="cl1-sim", samples=3, benchmark=lambda: next(seq)
        )
        with self.assertRaisesRegex(ValueError, "unstable"):
            supervisor.run("Improve")
        self.assertEqual(agent.goals, [])

    def test_rejected_candidate_rolls_back_on_regression(self):
        agent = MockAgent()
        seq = iter([Metrics(.72, 0, True)] * 3 + [Metrics(.82, 1, False)] * 3)
        report = RecursiveImprovement(
            agent, profile="cl1-sim", samples=3,
            benchmark=lambda: next(seq)
        ).run("Improve")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["cycles"][0]["decision"], "REJECT_VERIFICATION_FAILED")
        self.assertEqual(agent.rolled_back, ["m1"])

    def test_generic_profile_cannot_edit_cl1_target_without_its_benchmark(self):
        self.assertEqual(reject_unreviewed_scope([CL1_POLICY_PATH], "generic"), [CL1_POLICY_PATH])
        self.assertEqual(reject_unreviewed_scope([CL1_POLICY_PATH], "cl1-sim"), [])
        self.assertEqual(reject_unreviewed_scope([".github/workflows/rsi.yml"], "generic"), [".github/workflows/rsi.yml"])


if __name__ == "__main__":
    unittest.main()
