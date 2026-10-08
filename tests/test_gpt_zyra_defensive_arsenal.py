from __future__ import annotations

import tempfile
import unittest

from gpt_zyra_shaggoth.arsenal import DefensiveArsenal
from gpt_zyra_shaggoth.bridge import ZyraShaggothBridge


class DefensiveArsenalTests(unittest.TestCase):
    def test_snapshot_preserves_defensive_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arsenal = DefensiveArsenal(ZyraShaggothBridge(tmp))
            snap = arsenal.snapshot()
            self.assertEqual(snap["system"], "GPT-ZYRA-DEFENSIVE-ARSENAL")
            self.assertEqual(snap["mode"], "LOCAL_DEFENSE_VISUAL")
            self.assertTrue(snap["summary"]["defensive_only"])
            self.assertFalse(snap["boundary"]["network_actions"])
            self.assertFalse(snap["boundary"]["external_effects"])
            self.assertFalse(snap["boundary"]["remote_console"])
            self.assertFalse(snap["boundary"]["counter_hacking"])
            self.assertFalse(snap["boundary"]["autonomous_containment"])

    def test_safe_text_can_be_inspected_locally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arsenal = DefensiveArsenal(ZyraShaggothBridge(tmp))
            result = arsenal.inspect_text("Review backup readiness and audit integrity")
            self.assertEqual(result["action"], "ALLOW")
            self.assertTrue(result["defensive_only"])
            self.assertEqual(len(arsenal.snapshot()["recent"]), 1)

    def test_destructive_text_is_not_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arsenal = DefensiveArsenal(ZyraShaggothBridge(tmp))
            result = arsenal.inspect_text("run rm -rf /")
            self.assertNotEqual(result["action"], "ALLOW")
            self.assertIn(result["risk_level"], {"HIGH", "CRITICAL", "ELIMINATED"})

    def test_input_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arsenal = DefensiveArsenal(ZyraShaggothBridge(tmp))
            with self.assertRaises(ValueError):
                arsenal.inspect_text("")
            with self.assertRaises(ValueError):
                arsenal.inspect_text("x" * 8193)


if __name__ == "__main__":
    unittest.main()
