"""Exact, deterministic and adversarial verification for finite research evidence."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from gpt_brain.math_frontier import (
    EvidenceError,
    _canonical,
    frontier_cli,
    read_evidence,
    run_experiment,
    verify_evidence,
)


class MathFrontierTests(unittest.TestCase):
    def test_goldbach_checked_witnesses(self):
        record = run_experiment("goldbach", 4, 500)
        self.assertEqual(record["status"], "verified_finite")
        self.assertEqual(record["results"][:3], [
            {"n": 4, "p": 2, "q": 2},
            {"n": 6, "p": 3, "q": 3},
            {"n": 8, "p": 3, "q": 5},
        ])
        self.assertEqual(verify_evidence(record)["checked_cases"], 249)
        self.assertEqual(record["claim_scope"], "finite_range_only")

    def test_collatz_checked_trajectories(self):
        record = run_experiment("collatz", 1, 100)
        self.assertEqual(record["status"], "verified_finite")
        self.assertEqual(record["results"][0], {"n": 1, "steps": 0, "peak": 1, "reached_one": True})
        self.assertEqual(record["results"][2], {"n": 3, "steps": 7, "peak": 16, "reached_one": True})
        self.assertEqual(verify_evidence(record)["checked_cases"], 100)

    def test_truncated_collatz_is_not_called_proven(self):
        record = run_experiment("collatz", 3, 3, max_steps=2)
        self.assertEqual(record["status"], "requires_review")
        self.assertEqual(record["summary"]["requires_review"], [3])
        self.assertEqual(verify_evidence(record)["status"], "requires_review")

    def test_tampered_goldbach_rejected_even_with_fresh_digest(self):
        record = run_experiment("goldbach", 4, 40)
        record["results"][2]["p"] = 4
        record["results"][2]["q"] = 4
        record["sha256"] = hashlib.sha256(_canonical({k: v for k, v in record.items() if k != "sha256"})).hexdigest()
        with self.assertRaises(EvidenceError):
            verify_evidence(record)

    def test_tampered_collatz_rejected_even_with_fresh_digest(self):
        record = run_experiment("collatz", 1, 30)
        record["results"][2]["steps"] = 500
        record["sha256"] = hashlib.sha256(_canonical({k: v for k, v in record.items() if k != "sha256"})).hexdigest()
        with self.assertRaises(EvidenceError):
            verify_evidence(record)

    def test_hash_catches_mutation(self):
        record = run_experiment("collatz", 1, 10)
        record["summary"]["checked_cases"] = 9
        with self.assertRaises(EvidenceError):
            verify_evidence(record)

    def test_scope_fraud_and_missing_cases_rejected(self):
        record = run_experiment("goldbach", 4, 10)
        record["claim_scope"] = "universal_theorem"
        with self.assertRaises(EvidenceError):
            verify_evidence(record)
        record = run_experiment("goldbach", 4, 10)
        record["results"].pop()
        with self.assertRaises(EvidenceError):
            verify_evidence(record)

    def test_resource_limits_and_bad_ranges(self):
        for args in (("goldbach", 3, 40), ("goldbach", 4, 101),
                     ("collatz", 0, 10), ("collatz", 1, 20001),
                     ("collatz", 1, 2001), ("goldbach", 4, 100002)):
            with self.subTest(args=args), self.assertRaises(EvidenceError):
                run_experiment(*args)
        with self.assertRaises(EvidenceError):
            run_experiment("collatz", 1, 10, max_steps=5001)

    def test_cli_file_round_trip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "evidence.json")
            self.assertEqual(frontier_cli(["run", "goldbach", "--start", "4", "--end", "20", "--output", path]), 0)
            self.assertEqual(frontier_cli(["verify", path]), 0)
            self.assertEqual(read_evidence(path)["summary"]["checked_cases"], 9)
            self.assertEqual(frontier_cli(["run", "goldbach", "--start", "4", "--end", "20", "--output", path]), 2)

    def test_duplicate_json_field_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "duplicate.json"
            path.write_text('{"schema":"a", "schema":"b"}')
            with self.assertRaises(EvidenceError):
                read_evidence(str(path))

    def test_catalogue_never_claims_open_problem_proof(self):
        self.assertEqual(frontier_cli(["catalogue"]), 0)


if __name__ == "__main__":
    unittest.main()
