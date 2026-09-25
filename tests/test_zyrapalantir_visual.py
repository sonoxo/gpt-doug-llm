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
        self.assertIn("Human approval required", html)
        self.assertIn("Auto external action disabled", html)
        self.assertIn("no Foundry write or external action", html)

    def test_all_navigation_views_are_wired(self):
        html = (ROOT / "web" / "zyrapalantir-field" / "index.html").read_text(encoding="utf-8")
        for view in ("terminal", "investigations", "proposals", "readiness", "audit", "maven", "ontology"):
            self.assertIn(f'data-view="{view}"', html)
        for endpoint in ("/api/investigations", "/api/proposals", "/api/audit", "/api/maven-proof", "/api/ontology"):
            self.assertIn(endpoint, html)
        self.assertIn("function goBack()", html)
        self.assertIn("onclick=\"goBack()\"", html)

    def test_maven_proof_toggle_is_wired(self):
        html = (ROOT / "web" / "zyrapalantir-field" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="mavenToggle"', html)
        self.assertIn('id="mavenDrawer"', html)
        self.assertIn("function toggleMavenProof", html)
        self.assertIn("localStorage.setItem('zyra.mavenProofOpen'", html)

    def test_system_and_ontology_connectors_are_clickable(self):
        html = (ROOT / "web" / "zyrapalantir-field" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-edge="LOCAL HOST → MAVEN"', html)
        self.assertIn("showSystemEdge", html)
        self.assertIn("ontologyConnector", html)
        self.assertIn("showOntologyEdge", html)

    def test_ontology_loads_and_validates_connectors(self):
        mod = load_visual()
        payload = mod.ontology_payload()
        self.assertTrue(payload["nodes"])
        self.assertTrue(payload["links"])
        self.assertEqual(payload["session"]["status"], "STANDBY")
        self.assertFalse(payload["foundry_write"])
        self.assertFalse(payload["external_action"])

    def test_ontology_initiation_is_local_and_audited(self):
        mod = load_visual()
        result = mod.initiate_ontology()
        self.assertTrue(result["ok"])
        self.assertGreater(result["node_count"], 0)
        self.assertGreater(result["link_count"], 0)
        self.assertFalse(result["foundry_write"])
        self.assertFalse(result["automatic_external_action"])
        self.assertEqual(result["ontology"]["session"]["status"], "ACTIVE")

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

    def test_assistant_reports_ontology(self):
        mod = load_visual()
        reply = mod.assistant_reply("show maven ontology", {})
        self.assertIn("objects", reply)
        self.assertIn("connectors", reply)
        self.assertIn("no Foundry write", reply)

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
