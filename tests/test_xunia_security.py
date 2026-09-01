import unittest
from dataclasses import replace
from datetime import datetime, timezone

from xunia_security import Engagement, SecurityMode, Target, XuniaSecurityPlatform, target_authorized


NOW = datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc)


def engagement(mode=SecurityMode.PENTEST):
    return Engagement(
        engagement_id="gpt-demo-001",
        owner="security-owner",
        mode=mode,
        starts_at=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
        targets=(Target("url", "https://lab.example.test"),),
        exclusions=(Target("url", "https://lab.example.test/billing"),),
        allowed_checks=("service.discovery", "web.templates", "web.baseline", "supply-chain.sbom"),
        authorization_reference="AUTH-GPT-001",
    )


class XuniaSecurityPlatformTests(unittest.TestCase):
    def test_pentest_plans_safe_active_without_destructive_actions(self):
        plan = XuniaSecurityPlatform().plan(engagement(), NOW)
        self.assertEqual(plan.destructive_actions, "DENIED")
        self.assertEqual([step.tool.id for step in plan.steps], ["nmap", "nuclei", "zap-baseline", "syft"])
        self.assertEqual(plan.steps[0].argv[0], "nmap")
        self.assertTrue(plan.steps[0].evidence_id)

    def test_assess_drops_safe_active_tool(self):
        plan = XuniaSecurityPlatform().plan(engagement(SecurityMode.ASSESS), NOW)
        self.assertNotIn("nuclei", [step.tool.id for step in plan.steps])
        self.assertIn("nmap", [step.tool.id for step in plan.steps])

    def test_explicit_exclusion_blocks_nested_target(self):
        e = engagement()
        self.assertFalse(target_authorized(e, Target("url", "https://lab.example.test/billing")))
        self.assertTrue(target_authorized(e, Target("url", "https://lab.example.test/api")))

    def test_expired_authorization_cannot_plan(self):
        with self.assertRaises(PermissionError):
            XuniaSecurityPlatform().plan(e := engagement(), datetime(2026, 9, 3, tzinfo=timezone.utc))

    def test_destructive_engagement_is_rejected(self):
        e = replace(engagement(), destructive_allowed=True)
        with self.assertRaisesRegex(ValueError, "DESTRUCTIVE_ACTIONS_NOT_SUPPORTED"):
            XuniaSecurityPlatform().plan(e, NOW)

    def test_tampered_command_fails_integrity_check(self):
        e = engagement()
        platform = XuniaSecurityPlatform()
        step = platform.plan(e, NOW).steps[0]
        tampered = replace(step, argv=("sh", "-c", "echo unsafe"))
        with self.assertRaisesRegex(PermissionError, "COMMAND_INTEGRITY_CHECK_FAILED"):
            platform.authorize_step(e, tampered, NOW)


if __name__ == "__main__":
    unittest.main()
