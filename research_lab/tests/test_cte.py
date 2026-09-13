import json
import os
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

    def test_cli_rejects_boolean_approval_bypass(self):
        root = Path(__file__).resolve().parents[2]

        payload = {
            "state": {
                "version": "ontology-v1",
                "objects": {"service": {"status": "online"}},
            },
            "transition": {
                "transition_id": "tx-cli-bypass",
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

        self.assertEqual(result.returncode, 2)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "ERROR")
        self.assertIn("human_approved", output["message"])

    def test_cli_executes_only_with_receipt(self):
        from research_lab.approval import digest
        from research_lab.cte import ReceiptAuthorizer

        root = Path(__file__).resolve().parents[2]

        state = StateSnapshot(
            version="ontology-v1",
            objects={"service": {"status": "online"}},
        )

        transition = ProposedTransition(
            transition_id="tx-cli-receipt",
            actor="gpt-doug",
            changes={"service": {"status": "maintenance"}},
            required_policy="policy-v1",
        )

        code_versions = {
            "cte-engine": digest("cte-code-v1"),
        }

        data_versions = {
            "ontology-schema": digest("schema-v1"),
        }

        policy_versions = {
            "policy-v1": digest("policy-content-v1"),
        }

        with tempfile.TemporaryDirectory() as directory:
            database = str(
                Path(directory) / "cte-approvals.sqlite"
            )

            authorizer = ReceiptAuthorizer(
                database,
                {"human-reviewer"},
            )

            try:
                token = authorizer.issue(
                    state,
                    transition,
                    code_versions,
                    data_versions,
                    policy_versions,
                    "human-reviewer",
                    now=1000.0,
                    ttl=300,
                )
            finally:
                authorizer.close()

            payload = {
                "state": {
                    "version": state.version,
                    "objects": state.objects,
                },
                "transition": {
                    "transition_id": transition.transition_id,
                    "actor": transition.actor,
                    "changes": transition.changes,
                    "required_policy": transition.required_policy,
                },
                "approval_database": database,
                "code_versions": code_versions,
                "data_versions": data_versions,
                "policy_versions": policy_versions,
                "now": 1001.0,
            }

            source = Path(directory) / "cte-execute.json"
            source.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["ZYRA_CTE_APPROVERS"] = "human-reviewer"
            env["ZYRA_CTE_RECEIPT"] = token

            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/invention_lab.py"),
                    "cte-execute",
                    str(source),
                ],
                capture_output=True,
                text=True,
                env=env,
            )

        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "COMMITTED")


class TestCTEAuthorizationReceipts(unittest.TestCase):
    def setUp(self):
        from research_lab.approval import digest
        from research_lab.cte import ReceiptAuthorizer

        self.directory = tempfile.TemporaryDirectory()

        self.authorizer = ReceiptAuthorizer(
            str(Path(self.directory.name) / "cte-approvals.sqlite"),
            {"human-reviewer"},
        )

        self.state = StateSnapshot(
            version="ontology-v1",
            objects={"service": {"status": "online"}},
        )

        self.transition = ProposedTransition(
            transition_id="tx-auth-001",
            actor="gpt-doug",
            changes={"service": {"status": "maintenance"}},
            required_policy="policy-v1",
        )

        self.code_versions = {
            "cte-engine": digest("cte-code-v1"),
        }

        self.data_versions = {
            "ontology-schema": digest("schema-v1"),
        }

        self.policy_versions = {
            "policy-v1": digest("policy-content-v1"),
        }

    def tearDown(self):
        self.authorizer.close()
        self.directory.cleanup()

    def issue(self):
        return self.authorizer.issue(
            self.state,
            self.transition,
            self.code_versions,
            self.data_versions,
            self.policy_versions,
            "human-reviewer",
            now=1000.0,
            ttl=300,
        )

    def test_valid_receipt_commits(self):
        token = self.issue()

        result = self.authorizer.execute(
            token,
            self.state,
            self.transition,
            self.code_versions,
            self.data_versions,
            self.policy_versions,
            now=1001.0,
        )

        self.assertEqual(result.status, "COMMITTED")

    def test_receipt_cannot_be_replayed(self):
        token = self.issue()

        first = self.authorizer.execute(
            token,
            self.state,
            self.transition,
            self.code_versions,
            self.data_versions,
            self.policy_versions,
            now=1001.0,
        )

        second = self.authorizer.execute(
            token,
            self.state,
            self.transition,
            self.code_versions,
            self.data_versions,
            self.policy_versions,
            now=1002.0,
        )

        self.assertEqual(first.status, "COMMITTED")
        self.assertEqual(second.status, "AUTHORIZATION_DENIED")

    def test_state_change_invalidates_receipt(self):
        token = self.issue()

        changed_state = StateSnapshot(
            version="ontology-v1",
            objects={"service": {"status": "degraded"}},
        )

        result = self.authorizer.execute(
            token,
            changed_state,
            self.transition,
            self.code_versions,
            self.data_versions,
            self.policy_versions,
            now=1001.0,
        )

        self.assertEqual(result.status, "AUTHORIZATION_DENIED")

    def test_policy_change_invalidates_receipt(self):
        from research_lab.approval import digest

        token = self.issue()

        changed_policy_versions = {
            "policy-v1": digest("policy-content-v2"),
        }

        result = self.authorizer.execute(
            token,
            self.state,
            self.transition,
            self.code_versions,
            self.data_versions,
            changed_policy_versions,
            now=1001.0,
        )

        self.assertEqual(result.status, "AUTHORIZATION_DENIED")


    def test_attempt_id_binds_exact_state_snapshot(self):
        from research_lab.cte import ExecutionJournal

        journal = ExecutionJournal(
            str(Path(self.directory.name) / "state-journal.sqlite")
        )

        try:
            self.authorizer.begin_attempt(
                journal,
                "attempt-state",
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1000,
            )

            changed_state = StateSnapshot(
                version=self.state.version,
                objects={"service": {"status": "degraded"}},
            )

            with self.assertRaises(ValueError):
                self.authorizer.begin_attempt(
                    journal,
                    "attempt-state",
                    changed_state,
                    self.transition,
                    self.code_versions,
                    self.data_versions,
                    self.policy_versions,
                    now=1001,
                )
        finally:
            journal.close()

    def test_attempt_id_binds_exact_policy_snapshot(self):
        from research_lab.approval import digest
        from research_lab.cte import ExecutionJournal

        journal = ExecutionJournal(
            str(Path(self.directory.name) / "policy-journal.sqlite")
        )

        try:
            self.authorizer.begin_attempt(
                journal,
                "attempt-policy",
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1000,
            )

            changed_policy = {
                "policy-v1": digest("policy-content-v2"),
            }

            with self.assertRaises(ValueError):
                self.authorizer.begin_attempt(
                    journal,
                    "attempt-policy",
                    self.state,
                    self.transition,
                    self.code_versions,
                    self.data_versions,
                    changed_policy,
                    now=1001,
                )
        finally:
            journal.close()


    def test_durable_execution_records_full_lifecycle(self):
        from research_lab.cte import ExecutionJournal

        token = self.issue()

        journal = ExecutionJournal(
            str(Path(self.directory.name) / "durable.sqlite")
        )

        try:
            result = self.authorizer.execute_durable(
                journal,
                "attempt-durable",
                token,
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1001,
            )

            self.assertEqual(result.status, "COMMITTED")

            self.assertEqual(
                [event.to_phase for event in journal.events("attempt-durable")],
                [
                    "PROPOSED",
                    "SIMULATED",
                    "AUTHORIZED",
                    "EXECUTING",
                    "OBSERVED",
                    "COMMITTED",
                ],
            )
        finally:
            journal.close()

    def test_durable_terminal_replay_is_idempotent(self):
        from research_lab.cte import ExecutionJournal

        token = self.issue()

        journal = ExecutionJournal(
            str(Path(self.directory.name) / "replay.sqlite")
        )

        try:
            first = self.authorizer.execute_durable(
                journal,
                "attempt-replay",
                token,
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1001,
            )

            second = self.authorizer.execute_durable(
                journal,
                "attempt-replay",
                token,
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1002,
            )

            self.assertEqual(first.status, "COMMITTED")
            self.assertEqual(second.status, "COMMITTED")
            self.assertEqual(
                len(journal.events("attempt-replay")),
                6,
            )
        finally:
            journal.close()

    def test_durable_drift_rolls_back(self):
        from research_lab.cte import ExecutionJournal

        token = self.issue()

        journal = ExecutionJournal(
            str(Path(self.directory.name) / "rollback.sqlite")
        )

        try:
            result = self.authorizer.execute_durable(
                journal,
                "attempt-rollback",
                token,
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1001,
                observed_override={
                    "service": {"status": "error"},
                },
            )

            self.assertEqual(result.status, "ROLLED_BACK")
            self.assertEqual(
                journal.get("attempt-rollback").phase,
                "ROLLED_BACK",
            )
        finally:
            journal.close()

    def test_nonterminal_retry_fails_closed_for_recovery(self):
        from research_lab.cte import ExecutionJournal

        token = self.issue()

        journal = ExecutionJournal(
            str(Path(self.directory.name) / "recovery.sqlite")
        )

        try:
            self.authorizer.begin_attempt(
                journal,
                "attempt-recovery",
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1000,
            )

            journal.advance(
                "attempt-recovery",
                "SIMULATED",
                1000,
                {"synthetic_crash_point": True},
            )

            result = self.authorizer.execute_durable(
                journal,
                "attempt-recovery",
                token,
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1001,
            )

            self.assertEqual(
                result.status,
                "RECOVERY_REQUIRED",
            )

            self.assertEqual(
                journal.get("attempt-recovery").phase,
                "SIMULATED",
            )

            # Recovery refusal occurs before receipt consumption.
            legacy = self.authorizer.execute(
                token,
                self.state,
                self.transition,
                self.code_versions,
                self.data_versions,
                self.policy_versions,
                now=1002,
            )

            self.assertEqual(legacy.status, "COMMITTED")
        finally:
            journal.close()


if __name__ == "__main__":
    unittest.main()
