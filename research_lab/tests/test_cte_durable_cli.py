import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research_lab.approval import digest
from research_lab.cte import (
    ProposedTransition,
    ReceiptAuthorizer,
    StateSnapshot,
)


class TestCTEDurableCLI(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(__file__).resolve().parents[2]

        self.approval_database = str(
            Path(self.directory.name) / "approvals.sqlite"
        )

        self.journal_database = str(
            Path(self.directory.name) / "journal.sqlite"
        )

        self.state = StateSnapshot(
            version="ontology-v1",
            objects={
                "service": {
                    "status": "online",
                }
            },
        )

        self.transition = ProposedTransition(
            transition_id="tx-cli-durable",
            actor="gpt-doug",
            changes={
                "service": {
                    "status": "maintenance",
                }
            },
            required_policy="policy-v1",
        )

        self.code_versions = {
            "cte-engine": digest("cte-code-v2"),
        }

        self.data_versions = {
            "ontology-schema": digest("schema-v1"),
        }

        self.policy_versions = {
            "policy-v1": digest("policy-v1"),
        }

    def tearDown(self):
        self.directory.cleanup()

    def issue(self):
        authorizer = ReceiptAuthorizer(
            self.approval_database,
            {"human-reviewer"},
        )

        try:
            return authorizer.issue(
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                "human-reviewer",
                now=1000,
                ttl=300,
            )
        finally:
            authorizer.close()

    def payload(self, attempt_id="attempt-cli-1"):
        return {
            "state": {
                "version": self.state.version,
                "objects": self.state.objects,
            },
            "transition": {
                "transition_id": (
                    self.transition.transition_id
                ),
                "actor": self.transition.actor,
                "changes": self.transition.changes,
                "required_policy": (
                    self.transition.required_policy
                ),
            },
            "approval_database": self.approval_database,
            "journal_database": self.journal_database,
            "attempt_id": attempt_id,
            "code_versions": self.code_versions,
            "data_versions": self.data_versions,
            "policy_versions": self.policy_versions,
            "now": 1001,
        }

    def run_cli(self, command, payload, receipt=None):
        source = (
            Path(self.directory.name)
            / f"{command}.json"
        )

        source.write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["ZYRA_CTE_APPROVERS"] = "human-reviewer"

        if receipt is not None:
            env["ZYRA_CTE_RECEIPT"] = receipt
        else:
            env.pop("ZYRA_CTE_RECEIPT", None)

        return subprocess.run(
            [
                sys.executable,
                str(
                    self.root
                    / "scripts"
                    / "invention_lab.py"
                ),
                command,
                str(source),
            ],
            capture_output=True,
            text=True,
            env=env,
        )

    def test_durable_cli_commits(self):
        token = self.issue()

        result = self.run_cli(
            "cte-execute-durable",
            self.payload(),
            receipt=token,
        )

        self.assertEqual(result.returncode, 0)

        output = json.loads(result.stdout)

        self.assertEqual(
            output["status"],
            "COMMITTED",
        )

        self.assertEqual(
            output["journal_phase"],
            "COMMITTED",
        )

    def test_status_exposes_lifecycle(self):
        token = self.issue()
        payload = self.payload(
            attempt_id="attempt-status",
        )

        execute = self.run_cli(
            "cte-execute-durable",
            payload,
            receipt=token,
        )

        self.assertEqual(execute.returncode, 0)

        status = self.run_cli(
            "cte-status",
            {
                "journal_database": (
                    self.journal_database
                ),
                "attempt_id": "attempt-status",
            },
        )

        self.assertEqual(status.returncode, 0)

        output = json.loads(status.stdout)

        self.assertEqual(
            output["status"],
            "FOUND",
        )

        self.assertEqual(
            [
                event["to_phase"]
                for event in output["events"]
            ],
            [
                "PROPOSED",
                "SIMULATED",
                "AUTHORIZED",
                "EXECUTING",
                "OBSERVED",
                "COMMITTED",
            ],
        )

    def test_terminal_cli_replay_is_idempotent(self):
        token = self.issue()

        payload = self.payload(
            attempt_id="attempt-replay-cli",
        )

        first = self.run_cli(
            "cte-execute-durable",
            payload,
            receipt=token,
        )

        second = self.run_cli(
            "cte-execute-durable",
            payload,
            receipt=token,
        )

        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)

        self.assertEqual(
            json.loads(second.stdout)["status"],
            "COMMITTED",
        )

    def test_attempt_binding_change_fails_closed(self):
        token = self.issue()

        payload = self.payload(
            attempt_id="attempt-bound-cli",
        )

        first = self.run_cli(
            "cte-execute-durable",
            payload,
            receipt=token,
        )

        self.assertEqual(first.returncode, 0)

        changed = self.payload(
            attempt_id="attempt-bound-cli",
        )

        changed["state"]["objects"] = {
            "service": {
                "status": "degraded",
            }
        }

        second = self.run_cli(
            "cte-execute-durable",
            changed,
            receipt=token,
        )

        self.assertEqual(second.returncode, 2)

        output = json.loads(second.stdout)

        self.assertEqual(
            output["status"],
            "ERROR",
        )

        self.assertIn(
            "different request",
            output["message"],
        )


if __name__ == "__main__":
    unittest.main()
