"""Offline Guardian safety acceptance (no third-party packages)."""
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gpt_doug_guardian import GuardianSim, GuardianError, OWNER, MODE, default_scenario


class GuardianChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "GPT_DOUG_AI_BLOCK_ALL": "0", "GPT_DOUG_AI_STOP_DIR": self.tmp.name,
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_owner_mode_and_no_external_effect(self):
        s = GuardianSim().snapshot()
        self.assertEqual(s["ownerAttribution"], OWNER)
        self.assertEqual(s["mode"], MODE)
        self.assertTrue(s["syntheticOnly"])
        for key in ("weaponCapabilities", "targeting", "physicalActuation",
                    "networkConnections", "unboundedReplication"):
            self.assertFalse(s["policy"][key])

    def test_deterministic_replay_and_audit(self):
        a = GuardianSim().run(40)
        self.assertEqual(a, GuardianSim().run(40))
        self.assertTrue(a["auditValid"])

    def test_safe_automatic_tasks_only(self):
        state = GuardianSim().run(60)
        incidents = {item["kind"]: item["status"] for item in state["incidents"]}
        self.assertEqual(incidents["survey"], "COMPLETE")
        self.assertEqual(incidents["inspection"], "COMPLETE")
        self.assertEqual(incidents["relay"], "PENDING")

    def test_approval_and_dual_review(self):
        sim = GuardianSim()
        sim.inject(incident_id="HIGH", kind="rescue", x=15, y=12, severity=5)
        sim.approve("HIGH", "opA")
        with self.assertRaises(PermissionError):
            sim.approve("HIGH", "opA")
        self.assertEqual(sim.run(1)["incidents"][-1]["status"], "PENDING")
        sim.approve("HIGH", "opB")
        self.assertEqual(sim.run(70)["incidents"][-1]["status"], "COMPLETE")

    def test_emergency_latch_and_two_person_rearm(self):
        sim = GuardianSim()
        sim.emergency_stop("opA")
        with self.assertRaises(PermissionError):
            sim.step()
        with self.assertRaises(PermissionError):
            sim.resume("opA", "opA")
        sim.resume("opA", "opB")
        self.assertEqual(sim.step()["tick"], 1)

    def test_host_kill_switch(self):
        sim = GuardianSim()
        (Path(self.tmp.name) / "STOP").write_text("STOP", encoding="utf-8")
        with self.assertRaises(PermissionError):
            sim.step()

    def test_rejects_unsafe_coordinates_and_weapon_fields(self):
        for key in ("lat", "coordinates", "weapon", "target", "actuator", "ip_address"):
            scenario = default_scenario()
            scenario["units"][0][key] = "illegal"
            with self.subTest(field=key), self.assertRaises(GuardianError):
                GuardianSim(scenario)

    def test_energy_geofence_and_obstacles(self):
        sim = GuardianSim()
        sim.approve("EV-002", "opA")
        obstacles = set(map(tuple, sim.snapshot()["obstacles"]))
        for _ in range(70):
            for u in sim.step()["units"]:
                self.assertTrue(0 <= u["x"] < 26 and 0 <= u["y"] < 16)
                self.assertTrue(0 <= u["battery"] <= 100)
                self.assertNotIn((u["x"], u["y"]), obstacles)

    def test_audit_detects_tampering(self):
        sim = GuardianSim()
        sim.run(3)
        sim.audit[2]["action"] = "tampered"
        self.assertFalse(sim.verify_audit())

    def test_strict_capacity_and_synthetic_flag(self):
        bad = default_scenario()
        bad["syntheticOnly"] = False
        with self.assertRaises(GuardianError):
            GuardianSim(bad)
        bad = default_scenario()
        bad["units"] = bad["units"] * 3
        with self.assertRaises(GuardianError):
            GuardianSim(bad)


if __name__ == "__main__":
    unittest.main()
