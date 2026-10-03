import json
import unittest
from pathlib import Path

from nuclear.global_pipeline.pipeline import PipelineError, run

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "nuclear" / "global_pipeline" / "sample.synthetic.json"


class NuclearGlobalPipelineTests(unittest.TestCase):
    def test_synthetic_fixture_runs(self):
        payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
        result = run(payload)
        self.assertEqual(result["schema"], "xunia.zyra.nuclr-global-charge.v1")
        self.assertEqual(result["source"], "NUCLR")
        self.assertTrue(0 <= result["charge_component"] <= 100)
        self.assertTrue(result["advisory_only"])
        self.assertFalse(result["external_actuation"])
        self.assertEqual(len(result["regions"]), 2)

    def test_operational_control_fields_are_rejected(self):
        payload = {
            "schema": "xunia.zyra.nuclr-input.v1",
            "signals": [
                {
                    "region": "synthetic",
                    "provenance": "synthetic",
                    "availability_pct": 90,
                    "reporting_coverage_pct": 90,
                    "generation_pct_of_reference": 90,
                    "data_freshness_minutes": 10,
                    "shutdown": True,
                }
            ],
        }
        with self.assertRaises(PipelineError):
            run(payload)

    def test_non_public_non_synthetic_provenance_is_rejected(self):
        payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
        payload["signals"][0]["provenance"] = "restricted"
        with self.assertRaises(PipelineError):
            run(payload)


if __name__ == "__main__":
    unittest.main()
