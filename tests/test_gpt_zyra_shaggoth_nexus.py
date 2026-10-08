from __future__ import annotations

import unittest
from pathlib import Path

from gpt_zyra_shaggoth.nexus import build_nexus_snapshot, nexus_page


class ShoggothNexusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.defense = {
            "generated_at": "2026-10-08T20:00:00+00:00",
            "summary": {"healthy_controls": 8, "total_controls": 9, "defensive_only": True},
            "boundary": {
                "localhost_only": True,
                "network_actions": False,
                "external_effects": False,
                "remote_console": False,
            },
            "control_checks": {"journal_integrity": True, "state_private": False},
            "shield": {"stats": {"blocked": 3, "quarantined": 1}},
            "recent": [{"timestamp": "now", "risk_level": "LOW", "action": "ALLOW", "classification": "BENIGN", "sensitive": "never-export"}],
            "bridge": {"binding": {"repo_root": "/private/path"}},
        }

    def test_fail_closed_when_optional_runtime_unavailable(self) -> None:
        snap = build_nexus_snapshot(self.defense)
        self.assertEqual(snap["system"], "SHOGGOTH-NEXUS")
        self.assertEqual(snap["security"]["healthy_controls"], 8)
        self.assertFalse(snap["security"]["verified"])
        self.assertEqual(snap["swarm"]["state"], "UNAVAILABLE")
        self.assertIsNone(snap["swarm"]["capacity"])
        self.assertEqual(snap["brain"]["state"], "UNAVAILABLE")
        self.assertIsNone(snap["brain"]["memory_records"])
        self.assertTrue(snap["boundary"]["localhost_only"])
        self.assertFalse(snap["boundary"]["external_effects"])
        self.assertNotIn("never-export", repr(snap))
        self.assertNotIn("/private/path", repr(snap))

    def test_live_model_status_and_swarm_are_truthfully_projected(self) -> None:
        brain = {
            "readiness": {"core_ready": True, "model_ready": False},
            "memory": {"records": 19, "path": "/secret/path"},
            "ontology": {"available": True, "domains": ["science", "security"]},
            "provider": {"api_key": "secret-dont-export"},
        }
        swarm = {
            "status": "alive", "agent_capacity": 100,
            "atomic_stack_valid": True, "atomic_layer_count": 8,
            "capability_profile": "reasoning", "pid": 1234567,
        }
        snap = build_nexus_snapshot(self.defense, brain=brain, swarm=swarm)
        self.assertEqual(snap["brain"]["state"], "CORE_READY")
        self.assertFalse(snap["brain"]["model_ready"])
        self.assertEqual(snap["brain"]["memory_records"], 19)
        self.assertEqual(snap["brain"]["ontology_domains"], ["science", "security"])
        self.assertEqual(snap["swarm"]["state"], "ALIVE")
        self.assertEqual(snap["swarm"]["capacity"], 100)
        self.assertTrue(snap["swarm"]["atomic_stack_valid"])
        self.assertEqual(snap["swarm"]["atomic_layer_count"], 8)
        self.assertEqual(len(snap["atomic_layers"]), 8)
        self.assertNotIn("secret-dont-export", repr(snap))
        self.assertNotIn("1234567", repr(snap))

    def test_rejects_missing_safety_boundary(self) -> None:
        with self.assertRaises(ValueError):
            build_nexus_snapshot({"summary": {"defensive_only": True}})
        unsafe = dict(self.defense)
        unsafe["boundary"] = {"localhost_only": False, "external_effects": True}
        with self.assertRaises(ValueError):
            build_nexus_snapshot(unsafe)

    def test_nexus_html_is_self_contained_and_local_api_only(self) -> None:
        html = nexus_page()
        self.assertIn("SHOGGOTH NEXUS", html)
        self.assertIn("/api/nexus", html)
        self.assertIn("/api/inspect", html)
        self.assertNotIn("cdn.", html)
        self.assertNotIn("javascript:eval", html)
        self.assertIn("prefers-reduced-motion", html)


if __name__ == "__main__":
    unittest.main()
