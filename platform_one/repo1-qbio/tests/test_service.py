import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from core import OUTCOME_STATES  # noqa: E402
from service import analyze_payload, build_frames  # noqa: E402


class ServiceTests(unittest.TestCase):
    def sample_payload(self):
        return {
            "source_class": "SIMULATED",
            "window": 3,
            "frames": [
                {"t_ms": 0, "counts": [0, 0, 0, 0]},
                {"t_ms": 20, "counts": [1, 0, 1, 0]},
                {"t_ms": 40, "counts": [1, 1, 1, 0]},
            ],
        }

    def test_analysis_is_read_only_and_probabilities_sum_to_one(self):
        result = analyze_payload(self.sample_payload())
        self.assertFalse(result["physical_control"])
        self.assertFalse(result["quantum_hardware_claim"])
        probabilities = result["forecast"]["next_state_probabilities"]
        self.assertEqual(set(probabilities), set(OUTCOME_STATES))
        self.assertAlmostEqual(sum(probabilities.values()), 1.0, places=5)

    def test_rejects_fractional_counts(self):
        payload = self.sample_payload()
        payload["frames"][1]["counts"][1] = 1.5
        with self.assertRaises(ValueError):
            build_frames(payload)

    def test_rejects_unapproved_source_class(self):
        payload = self.sample_payload()
        payload["source_class"] = "REAL_CL1_TRUST_ME"
        with self.assertRaises(ValueError):
            analyze_payload(payload)

    def test_json_serializable(self):
        json.dumps(analyze_payload(self.sample_payload()), allow_nan=False)

    def test_rejects_subnormal_timestamp_interval(self):
        payload = self.sample_payload()
        payload["frames"] = [
            {"t_ms": 0.0, "counts": [1, 1]},
            {"t_ms": 5e-324, "counts": [1, 1]},
        ]
        with self.assertRaises(ValueError):
            analyze_payload(payload)

    def test_rejects_timestamp_that_overflows_float_conversion(self):
        payload = self.sample_payload()
        payload["frames"] = [
            {"t_ms": 0, "counts": [1, 1]},
            {"t_ms": 10 ** 400, "counts": [1, 1]},
        ]
        with self.assertRaises(ValueError):
            analyze_payload(payload)


if __name__ == "__main__":
    unittest.main()
