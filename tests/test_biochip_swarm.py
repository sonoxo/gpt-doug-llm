"""Tests for offline bounded BioChip swarm."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from threading import Event
from research_lab.biochip_swarm import BioChip, MAX_WORKERS, worker_task


class BioChipSwarmTests(unittest.TestCase):
    def test_deduplicates_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            chip = BioChip(Path(temp) / "state.db")
            try:
                first = chip.remember({"observation": "alpha"})
                second = chip.remember({"observation": "alpha"})
                self.assertEqual(first, second)
                self.assertEqual(chip.report()["memory_records"], 1)
            finally:
                chip.close()

    def test_workers_are_bounded_and_audited(self):
        with tempfile.TemporaryDirectory() as temp:
            chip = BioChip(Path(temp) / "state.db")
            try:
                for i in range(MAX_WORKERS):
                    worker_task(chip, i, 0, Event())
                self.assertEqual(chip.report()["memory_records"], MAX_WORKERS)
                self.assertEqual(chip.report()["audit_events"], MAX_WORKERS)
            finally:
                chip.close()

    def test_stopped_worker_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            chip = BioChip(Path(temp) / "state.db")
            stop = Event()
            stop.set()
            try:
                worker_task(chip, 0, 0, stop)
                self.assertEqual(chip.report()["memory_records"], 0)
            finally:
                chip.close()


if __name__ == "__main__":
    unittest.main()
