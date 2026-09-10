import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_visual():
    spec = importlib.util.spec_from_file_location("zyrapalantir_visual", ROOT / "scripts" / "zyrapalantir_visual.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class VisualFieldTests(unittest.TestCase):
    def test_dashboard_contains_safety_boundaries(self):
        html = (ROOT / "web" / "zyrapalantir-field" / "index.html").read_text(encoding="utf-8")
        self.assertIn("NON-GEOGRAPHIC", html)
        self.assertIn("Targeting control disabled", html)
        self.assertIn("Weapons control disabled", html)
        self.assertIn("auto action: false", html)

    def test_dashboard_controls_are_wired(self):
        html = (ROOT / "web" / "zyrapalantir-field" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-view="investigations"', html)
        self.assertIn('data-view="readiness"', html)
        self.assertIn('data-view="audit"', html)
        self.assertIn("/api/investigations", html)
        self.assertIn("/api/proposals", html)
        self.assertIn("/api/audit", html)
        self.assertIn("data-node=\"host\"", html)

    def test_assistant_is_readonly_summary(self):
        mod = load_visual()
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

    def test_investigations_are_human_controlled(self):
        mod = load_visual()
        state = {
            "cyber": {
                "findings": [
                    {
                        "severity": "HIGH",
                        "target": "training-endpoint",
                        "description": "Synthetic defensive finding",
                        "recommendation": "Review evidence",
                    }
                ]
            }
        }
        items = mod.investigations(state)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "ANALYST_REVIEW")
        self.assertTrue(items[0]["human_authorization_required"])
        self.assertFalse(items[0]["automatic_external_action"])

    def test_proposals_never_execute_external_action(self):
        mod = load_visual()
        state = {
            "cyber": {
                "findings": [
                    {
                        "severity": "MEDIUM",
                        "target": "local-host",
                        "description": "Configuration observation",
                        "recommendation": "Validate expected configuration",
                    }
                ]
            }
        }
        items = mod.proposals(state)
        self.assertTrue(items)
        self.assertTrue(all(item["external_action"] is False for item in items))


if __name__ == "__main__":
    unittest.main()
