"""CL1 culture evidence tests: no hardware, networking, or manufactured biology."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from research_lab import cl1_growth as growth

ROOT = Path(__file__).resolve().parents[1]


class CL1GrowthEvidenceTests(unittest.TestCase):
    def lab_observation(
        self,
        day: int,
        metric: str,
        value: float,
        *,
        digest: str = "a" * 64,
        origin: str = "LAB_OPERATOR_ATTESTED",
    ) -> dict:
        return {
            "timestamp_utc": (dt.datetime(2026, 10, 14, 10, tzinfo=dt.timezone.utc)
                              + dt.timedelta(days=day)).isoformat(),
            "day_in_culture": day,
            "origin": origin,
            "metric": metric,
            "value": value,
            "collector": "local-test-fixture",
            "method": "unverified-test-input",
            "evidence_sha256": digest,
        }

    def document(self, observations: list[dict]) -> dict:
        return {
            "schema": growth.SCHEMA,
            "culture_id": "CL1-TEST-FIXTURE",
            "specimen_class": "CL1_NEURAL_CULTURE",
            "observations": observations,
        }

    def test_empty_is_not_biological_growth(self):
        result = growth.assess(growth.template())
        self.assertEqual(result["status"], "NO_DIRECT_GROWTH_EVIDENCE")
        self.assertFalse(result["measured_culture_growth_confirmed"])
        self.assertFalse(result["connected_to_cl1"])
        self.assertEqual(result["total_observation_count"], 0)

    def test_simulator_spikes_do_not_imply_growth(self):
        record = self.lab_observation(
            1, "MEA_SPIKE_RATE_HZ", 3.5, origin="SDK_SIMULATOR"
        )
        result = growth.assess(self.document([record]))
        self.assertEqual(result["status"], "SIMULATOR_ONLY_NO_BIOLOGICAL_GROWTH_EVIDENCE")
        self.assertIsNone(result["coverage_change_percentage_points"])
        self.assertFalse(result["measured_culture_growth_confirmed"])

    def test_two_lab_records_describe_coverage_change_not_proliferation(self):
        data = self.document([
            self.lab_observation(1, "COVERAGE_PERCENT", 20, digest="a" * 64),
            self.lab_observation(8, "COVERAGE_PERCENT", 31.25, digest="b" * 64),
            self.lab_observation(8, "VIABILITY_PERCENT", 89, digest="c" * 64),
            self.lab_observation(8, "MEA_SPIKE_RATE_HZ", 9, digest="d" * 64),
        ])
        result = growth.assess(data)
        self.assertEqual(result["status"], "LAB_RECORDED_COVERAGE_INCREASE")
        self.assertAlmostEqual(result["coverage_change_percentage_points"], 11.25)
        self.assertAlmostEqual(result["latest_viability_percent"], 89)
        self.assertEqual(result["lab_attested_observation_count"], 4)
        self.assertFalse(result["measured_culture_growth_confirmed"])
        self.assertIn("ATTESTED", result["provenance_level"])
        self.assertIn("not proof", " ".join(result["limitations"]))

    def test_single_image_or_reused_digest_does_not_establish_morphology_trend(self):
        data = self.document([
            self.lab_observation(1, "COVERAGE_PERCENT", 12),
            self.lab_observation(8, "COVERAGE_PERCENT", 60),
        ])
        result = growth.assess(data)
        self.assertEqual(result["status"], "INSUFFICIENT_LONGITUDINAL_MICROSCOPY")
        self.assertIsNone(result["coverage_change_percentage_points"])

    def test_reject_false_growth_metrics_and_bad_evidence(self):
        variants = [
            {"metric": "MITOCHONDRIAL_HEALTH"},
            {"metric": "COVERAGE_PERCENT", "origin": "SDK_SIMULATOR"},
            {"value": 101},
            {"value": float("nan")},
            {"value": True},
            {"day_in_culture": -1},
            {"day_in_culture": True},
            {"timestamp_utc": "2026-10-14T10:00:00"},
            {"evidence_sha256": ""},
            {"collector": ""},
            {"method": ""},
        ]
        for fields in variants:
            observation = self.lab_observation(1, "COVERAGE_PERCENT", 12)
            observation.update(fields)
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                growth.assess(self.document([observation]))

    def test_limits_and_schema_enforced(self):
        with self.assertRaises(ValueError):
            growth.assess({"schema": "wrong", "observations": []})
        with self.assertRaises(ValueError):
            growth.assess(self.document([{}] * 1001))
        with self.assertRaises(ValueError):
            growth.assess({**self.document([]), "culture_id": "<script>"})

    def test_offline_html_has_no_external_asset_and_no_fabrication(self):
        result = growth.assess(growth.template())
        page = growth.html_document(result)
        self.assertIn("No real laboratory measurements supplied", page)
        self.assertIn("No biological growth or organoid has been claimed", page)
        self.assertIn("No live CL1 connection", page)
        self.assertNotIn("<script", page)
        self.assertNotIn('src="https:', page)

    def test_integrity_digest_is_not_automatically_truth_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.bin"
            path.write_bytes(b"simulated-test-fixture-not-biological-data")
            result = growth.digest_file(path)
            self.assertEqual(
                result["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            self.assertIn("not proof", result["meaning"])

    def test_gpt_doug_max_launcher_opens_offline_dashboard_without_browser(self):
        result = subprocess.run(
            ["bash", "scripts/doug-max", "cl1", "grow", "--no-open"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        output = json.loads(result.stdout)
        self.assertFalse(output["hardware_connected"])
        self.assertFalse(output["biological_growth_confirmed"])
        location = output["dashboard"]
        self.assertTrue(location.startswith("file://"))
        from urllib.parse import unquote, urlparse

        path = Path(unquote(urlparse(location).path))
        try:
            self.assertIn("Neural Culture Growth Evidence", path.read_text())
        finally:
            path.unlink(missing_ok=True)

    def test_template_and_status_are_network_free(self):
        doc = growth.template()
        self.assertEqual(doc["observations"], [])
        self.assertFalse(growth.sdk_status()["cl1_hardware_connection_confirmed"])
        self.assertTrue(growth.SOURCES)
        self.assertTrue(all(src["url"].startswith("https://") for src in growth.SOURCES))


if __name__ == "__main__":
    unittest.main()
