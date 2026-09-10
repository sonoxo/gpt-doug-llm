import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class VisualFieldTests(unittest.TestCase):
    def test_dashboard_contains_safety_boundaries(self):
        html = (ROOT / "web" / "zyrapalantir-field" / "index.html").read_text(encoding="utf-8")
        self.assertIn("NON-GEOGRAPHIC", html)
        self.assertIn("Targeting control disabled", html)
        self.assertIn("Weapons control disabled", html)
        self.assertIn("auto action: false", html)

    def test_assistant_is_readonly_summary(self):
        spec = importlib.util.spec_from_file_location("zyrapalantir_visual", ROOT / "scripts" / "zyrapalantir_visual.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        state = {
            "field_ready": True,
            "defense_profile_active": True,
            "live_service_running": True,
            "maven_ok": True,
            "redpanda_cpr_ok": True,
            "highest_severity": "LOW",
            "cyber": {"severity_counts": {"LOW": 1, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}},
        }
        reply = mod.assistant_reply("show readiness", state)
        self.assertIn("READY", reply)
        self.assertIn("Maven=PASS", reply)


if __name__ == "__main__":
    unittest.main()
