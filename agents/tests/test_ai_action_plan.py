import os
import unittest
from unittest.mock import patch

from agents.ai_action_plan import (
    CAPABILITIES,
    POLICY_MARKER,
    capability_snapshot,
    inject_policy,
    policy_text,
)


class AIActionPlanProfileTests(unittest.TestCase):
    def test_profile_covers_all_three_operational_pillars(self):
        pillars = {item.pillar for item in CAPABILITIES}
        self.assertIn("innovation", pillars)
        self.assertIn("infrastructure", pillars)
        self.assertIn("security", pillars)

    def test_injection_is_idempotent_and_preserves_user_content(self):
        source = [{"role": "user", "content": "build a local app"}]
        first = inject_policy(source)
        second = inject_policy(first)
        self.assertEqual(first, second)
        self.assertEqual(first[-1], source[0])
        self.assertEqual(sum(POLICY_MARKER in m.get("content", "") for m in first), 1)

    def test_user_can_quote_marker_without_suppressing_profile(self):
        source = [{"role": "user", "content": f"Explain {POLICY_MARKER} to me"}]
        prepared = inject_policy(source)
        system_markers = [
            message
            for message in prepared
            if message.get("role") == "system" and POLICY_MARKER in message.get("content", "")
        ]
        self.assertEqual(len(system_markers), 1)
        self.assertEqual(prepared[-1], source[0])

    def test_profile_can_be_disabled(self):
        with patch.dict(os.environ, {"GPT_DOUG_AI_ACTION_PLAN": "0"}, clear=False):
            source = [{"role": "user", "content": "hello"}]
            self.assertEqual(inject_policy(source), source)
            self.assertFalse(capability_snapshot()["enabled"])

    def test_policy_preserves_security_and_human_control(self):
        text = policy_text().lower()
        self.assertIn("security", text)
        self.assertIn("privacy", text)
        self.assertIn("human review", text)
        self.assertIn("do not claim u.s. government", text)

    def test_profile_includes_evaluation_and_incident_response(self):
        names = {item.capability for item in CAPABILITIES}
        self.assertIn("evaluation", names)
        self.assertIn("incident_response", names)
        self.assertIn("secure_by_design", names)


if __name__ == "__main__":
    unittest.main()
