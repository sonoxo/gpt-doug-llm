import tempfile
import unittest
from pathlib import Path

from research_lab.cte.journal import ExecutionJournal


class TestExecutionJournal(unittest.TestCase):
    def test_start_is_idempotent(self):
        journal = ExecutionJournal(":memory:")
        try:
            first = journal.start("a-1", "tx-1", "state-v1", 1)
            second = journal.start("a-1", "tx-1", "state-v1", 2)

            self.assertEqual(first.phase, "PROPOSED")
            self.assertEqual(second.phase, "PROPOSED")
            self.assertEqual(len(journal.events("a-1")), 1)
        finally:
            journal.close()

    def test_attempt_id_collision_is_rejected(self):
        journal = ExecutionJournal(":memory:")
        try:
            journal.start("a-1", "tx-1", "state-v1", 1)

            with self.assertRaises(ValueError):
                journal.start("a-1", "tx-2", "state-v1", 2)

            with self.assertRaises(ValueError):
                journal.start("a-1", "tx-1", "state-v2", 2)
        finally:
            journal.close()

    def test_full_commit_lifecycle(self):
        journal = ExecutionJournal(":memory:")
        try:
            journal.start("a-1", "tx-1", "state-v1", 1)

            phases = [
                "SIMULATED",
                "AUTHORIZED",
                "EXECUTING",
                "OBSERVED",
                "COMMITTED",
            ]

            for index, phase in enumerate(phases, start=2):
                journal.advance(
                    "a-1",
                    phase,
                    index,
                    {"phase": phase},
                )

            attempt = journal.get("a-1")
            self.assertEqual(attempt.phase, "COMMITTED")
            self.assertEqual(len(journal.events("a-1")), 6)

            with self.assertRaises(ValueError):
                journal.advance("a-1", "ROLLED_BACK", 8)
        finally:
            journal.close()

    def test_illegal_transition_is_rejected(self):
        journal = ExecutionJournal(":memory:")
        try:
            journal.start("a-1", "tx-1", "state-v1", 1)

            with self.assertRaises(ValueError):
                journal.advance("a-1", "AUTHORIZED", 2)

            self.assertEqual(journal.get("a-1").phase, "PROPOSED")
        finally:
            journal.close()

    def test_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "cte-journal.sqlite3"

            first = ExecutionJournal(database)
            first.start("a-1", "tx-1", "state-v1", 1)
            first.advance("a-1", "SIMULATED", 2, {"score": 1})
            first.close()

            second = ExecutionJournal(database)
            try:
                attempt = second.get("a-1")
                events = second.events("a-1")

                self.assertEqual(attempt.phase, "SIMULATED")
                self.assertEqual(events[-1].payload, {"score": 1})
            finally:
                second.close()

    def test_recovery_excludes_terminal_attempts(self):
        journal = ExecutionJournal(":memory:")
        try:
            journal.start("open", "tx-open", "state-v1", 1)
            journal.advance("open", "SIMULATED", 2)

            journal.start("done", "tx-done", "state-v1", 3)
            journal.advance("done", "SIMULATED", 4)
            journal.advance("done", "ROLLED_BACK", 5)

            recoverable = journal.recoverable()

            self.assertEqual(
                [attempt.attempt_id for attempt in recoverable],
                ["open"],
            )
        finally:
            journal.close()


    def test_attempt_request_binding_is_stable(self):
        journal = ExecutionJournal(":memory:")
        try:
            journal.start(
                "a-bound",
                "tx-bound",
                "state-v1",
                1,
                request_binding="digest-a",
            )

            journal.start(
                "a-bound",
                "tx-bound",
                "state-v1",
                2,
                request_binding="digest-a",
            )

            self.assertEqual(
                len(journal.events("a-bound")),
                1,
            )

            with self.assertRaises(ValueError):
                journal.start(
                    "a-bound",
                    "tx-bound",
                    "state-v1",
                    3,
                    request_binding="digest-b",
                )
        finally:
            journal.close()


if __name__ == "__main__":
    unittest.main()
