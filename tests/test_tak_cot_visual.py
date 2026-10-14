"""End-to-end visual CoT smoke tests; localhost only, no third-party TAK."""
from __future__ import annotations

import http.client
import json
import subprocess
import unittest
from pathlib import Path

import tak_cot_visual

ROOT = Path(__file__).resolve().parents[1]


class CoTVisualTests(unittest.TestCase):
    def test_local_udp_to_gateway_to_browser_map_route(self):
        handle = tak_cot_visual.start_dashboard(
            uid="LAB-VISIBLE-CI", kind="medical", lat=34.61, lon=-86.59
        )
        try:
            self.assertIn("127.0.0.1", handle["url"])
            self.assertIn("cot=LAB-VISIBLE-CI", handle["url"])
            self.assertEqual(handle["unit"]["id"], "LAB-VISIBLE-CI")
            self.assertEqual(handle["unit"]["source"], "legacy-udp-loopback")
            self.assertTrue(handle["unit"]["synthetic"])
            self.assertAlmostEqual(handle["unit"]["lat"], 34.61)
            self.assertAlmostEqual(handle["unit"]["lon"], -86.59)

            response = tak_cot_visual._snapshot(handle["http_port"])
            self.assertTrue(any(u["id"] == "LAB-VISIBLE-CI" for u in response["units"]))
            connection = http.client.HTTPConnection(
                "127.0.0.1", handle["http_port"], timeout=3
            )
            try:
                connection.request("GET", "/")
                response = connection.getresponse()
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("GPT-DOUG TAK-OS", body)
            finally:
                connection.close()
        finally:
            tak_cot_visual.stop_dashboard(handle)

    def test_visual_launcher_help_from_gpt_doug_max(self):
        result = subprocess.run(
            ["bash", "scripts/doug-max", "cot", "show", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        self.assertIn("--no-open", result.stdout)
        self.assertIn("--lat", result.stdout)

    def test_browser_focus_requires_received_synthetic_gateway_unit(self):
        app = (ROOT / "docs/tak-os/app.js").read_text(encoding="utf-8")
        bridge = (ROOT / "docs/tak-os/bridge.js").read_text(encoding="utf-8")
        self.assertIn("focusGatewayUnit(uid)", app)
        self.assertIn("unit.synthetic === true", app)
        self.assertIn("state.selected = unit.id", app)
        self.assertIn("setMapCenter({lat: unit.lat, lon: unit.lon})", app)
        self.assertIn("focusReceived();", bridge)
        self.assertIn("searchParams.get('cot')", bridge)

    def test_invalid_marker_fails_before_local_server_starts(self):
        with self.assertRaises(ValueError):
            tak_cot_visual.start_dashboard(
                uid="HOSTILE-REAL", kind="medical", lat=34.61, lon=-86.59
            )
        with self.assertRaises(ValueError):
            tak_cot_visual.start_dashboard(
                uid="LAB-VISIBLE-FAIL", kind="hostile", lat=34.61, lon=-86.59
            )


if __name__ == "__main__":
    unittest.main()
