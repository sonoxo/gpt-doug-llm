"""Physics floor and RAM budget regression tests."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from research_lab.light_ram_budget import build_report, light_latency


class LightRamTests(unittest.TestCase):
    def test_speed_of_light_1m(self):
        p = light_latency(1, 1)
        self.assertAlmostEqual(p["one_way_ns_floor"], 3.335641, places=5)
        self.assertAlmostEqual(p["round_trip_ns_floor"], 6.671282, places=5)

    def test_cable_slower_than_vacuum(self):
        self.assertGreater(light_latency(0.1, .67)["round_trip_ns_floor"], light_latency(0.1, 1)["round_trip_ns_floor"])

    def test_zero_distance_has_no_clock_claim(self):
        self.assertIsNone(light_latency(0, 1)["serial_round_trip_hz_ceiling"])

    def test_invalid_inputs(self):
        for d, speed in [(-1, 1), (1, 0), (1, 1.1)]:
            with self.assertRaises(ValueError):
                light_latency(d, speed)
        with self.assertRaises(ValueError):
            build_report(1, 1, 1)

    def test_uses_available_not_installed(self):
        with patch("research_lab.light_ram_budget.local_ram_bytes", return_value=(64 * 1024**3, 10 * 1024**3, "test")):
            report = build_report(.1, .67, .25)
        self.assertEqual(report["memory"]["suggested_additional_workload_budget_bytes"], int(10 * 1024**3 * .75))

    def test_macos_unknown_availability(self):
        with patch("research_lab.light_ram_budget.local_ram_bytes", return_value=(64 * 1024**3, None, "test")):
            report = build_report(.1, .67, .25)
        self.assertIsNone(report["memory"]["suggested_additional_workload_budget_bytes"])


if __name__ == "__main__":
    unittest.main()
