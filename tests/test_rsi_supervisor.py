import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from rsi_supervisor import Metrics, RecursiveImprovement, ExternalBenchmark, measured_gain


class FakeAgent:
    def __init__(self, missions, ok=True):
        self.missions = iter(missions)
        self.ok = ok
        self.rolled_back = []

    def run(self, goal, *, evolve=False):
        assert evolve
        return next(self.missions)

    def rollback(self, mission_id):
        self.rolled_back.append(mission_id)
        return {"rolled_back": True}

    def _tool_run_check(self, check, touched):
        return {"check": check, "ok": self.ok}

    def _run_process(self, args, *, timeout):
        assert args == ["git", "diff", "--check"]
        return {"ok": True}


def mission(mid, status="PASS", changed=True, syntax=True):
    return SimpleNamespace(mission_id=mid, status=status,
                           touched_files=["agents/example.py"] if changed else [],
                           checks=[{"check": "syntax", "ok": syntax}], rolled_back=False)


class RecursiveImprovementTests(unittest.TestCase):
    def test_two_measured_generations(self):
        agent = FakeAgent([mission("a"), mission("b")])
        samples = iter([Metrics(.5, 0, True), Metrics(.55, 0, True), Metrics(.61, 0, True)])
        report = RecursiveImprovement(agent, cycles=2, benchmark=lambda: next(samples)).run("Improve")
        self.assertEqual(report["status"], "MEASURED_GAIN_REVIEW_REQUIRED")
        self.assertEqual(len(report["cycles"]), 2)
        self.assertFalse(agent.rolled_back)

    def test_later_regression_rolls_back(self):
        agent = FakeAgent([mission("a"), mission("b")])
        samples = iter([Metrics(.5, 0, True), Metrics(.6, 0, True), Metrics(.7, 1, True)])
        report = RecursiveImprovement(agent, cycles=2, benchmark=lambda: next(samples)).run("Improve")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(agent.rolled_back, ["b"])

    def test_unmeasured_stops_after_one_round(self):
        agent = FakeAgent([mission("a"), mission("b")])
        report = RecursiveImprovement(agent, cycles=2).run("Improve")
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(len(report["cycles"]), 1)

    def test_failed_checks_rollback(self):
        agent = FakeAgent([mission("a")], ok=False)
        self.assertEqual(RecursiveImprovement(agent).run("Improve")["status"], "BLOCKED")
        self.assertEqual(agent.rolled_back, ["a"])

    def test_no_change_or_syntax_failure(self):
        for m in (mission("a", changed=False), mission("b", syntax=False)):
            with self.subTest(m=m.mission_id):
                agent = FakeAgent([m])
                self.assertEqual(RecursiveImprovement(agent).run("Improve")["status"], "BLOCKED")
                self.assertEqual(agent.rolled_back, [m.mission_id])

    def test_failed_agent_rollback(self):
        agent = FakeAgent([mission("a", status="FAIL")])
        self.assertEqual(RecursiveImprovement(agent).run("Improve")["status"], "BLOCKED")
        self.assertEqual(agent.rolled_back, ["a"])

    def test_metrics_reject_bad_data(self):
        for item in [
            {"quality": True, "regressions": 0, "security_ok": True},
            {"quality": float("nan"), "regressions": 0, "security_ok": True},
            {"quality": .5, "regressions": -1, "security_ok": True},
            {"quality": .5, "regressions": 0, "security_ok": 1},
        ]:
            with self.subTest(item=item), self.assertRaises(ValueError):
                Metrics.from_json(item)

    def test_security_and_minimum_gain(self):
        base = Metrics(.5, 0, True)
        self.assertTrue(measured_gain(base, Metrics(.52, 0, True), .01)[0])
        for candidate in (Metrics(.8, 1, True), Metrics(.8, 0, False), Metrics(.505, 0, True)):
            self.assertFalse(measured_gain(base, candidate, .01)[0])

    def test_external_benchmark_cannot_be_agent_editable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir()
            script = root / "eval.py"
            script.write_text("print('{}')\n")
            with self.assertRaises(ValueError):
                ExternalBenchmark(script, root)

    def test_budget(self):
        with self.assertRaises(ValueError):
            RecursiveImprovement(FakeAgent([]), cycles=4)


if __name__ == "__main__":
    unittest.main()
