import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_lab.cte import (
    CounterfactualTransactionEngine,
    ProposedTransition,
    StateSnapshot,
)


class TestCounterfactualTransactionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = CounterfactualTransactionEngine()
        self.state = StateSnapshot(
            version="ontology-v1",
            objects={"service": {"status": "online"}},
        )
        self.transition = ProposedTransition(
            transition_id="tx-001",
            actor="gpt-doug",
            changes={"service": {"status": "maintenance"}},
            required_policy="policy-v1",
        )

    def test_requires_human_review(self):
        result = self.engine.run(self.state, self.transition)
        self.assertEqual(result.status, "PENDING_HUMAN_REVIEW")

    def test_commit_after_approval(self):
        result = self.engine.run(
            self.state,
            self.transition,
            human_approved=True,
        )
        self.assertEqual(result.status, "COMMITTED")

    def test_drift_causes_rollback(self):
        result = self.engine.run(
            self.state,
            self.transition,
            human_approved=True,
            observed_override={"service": {"status": "error"}},
        )
        self.assertEqual(result.status, "ROLLED_BACK")

    def test_real_state_is_not_mutated_by_counterfactual(self):
        self.engine.run(
            self.state,
            self.transition,
            human_approved=True,
        )
        self.assertEqual(
            self.state.objects["service"]["status"],
            "online",
        )

    def test_cli_committed_transaction(self):
        root = Path(__file__).resolve().parents[2]
        payload = {
            "state": {
                "version": "ontology-v1",
                "objects": {"service": {"status": "online"}},
            },
            "transition": {
                "transition_id": "tx-cli-001",
                "actor": "gpt-doug",
                "changes": {"service": {"status": "maintenance"}},
                "required_policy": "policy-v1",
            },
            "human_approved": True,
        }

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "cte.json"
            source.write_text(json.dumps(payload), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/invention_lab.py"),
                    "cte",
                    str(source),
                ],
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "COMMITTED")


if __name__ == "__main__":
    unittest.main()
