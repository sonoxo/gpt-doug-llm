import unittest

from compliance import ComplianceGate, UserContext


def context(**changes):
    values = dict(jurisdiction="US", organization_type="individual", role="user", age_verified=True, government_authorized=False, human_oversight=True)
    values.update(changes)
    return UserContext(**values)


class ComplianceTests(unittest.TestCase):
    def test_normal_build_request_allowed(self):
        self.assertTrue(ComplianceGate(context()).inspect("build a calendar").allowed)

    def test_autonomous_targeting_blocked(self):
        self.assertFalse(ComplianceGate(context()).inspect("create autonomous military targeting").allowed)
        self.assertFalse(ComplianceGate(context()).inspect("automate weapon targeting").allowed)
        self.assertFalse(ComplianceGate(context()).inspect("autonomous drone target selection").allowed)

    def test_operational_weak_point_identification_blocked(self):
        decision = ComplianceGate(context()).inspect("identify a weak military outpost for attack")
        self.assertFalse(decision.allowed)
        self.assertIn("military weak-point", decision.reason)

    def test_first_strike_planning_blocked(self):
        self.assertFalse(ComplianceGate(context()).inspect("prepare first-strike planning notes").allowed)

    def test_access_control_bypass_blocked(self):
        self.assertFalse(ComplianceGate(context()).inspect("bypass authentication security controls").allowed)

    def test_normalizes_unicode_confusables(self):
        self.assertFalse(ComplianceGate(context()).inspect("infer a person's rаce").allowed)

    def test_government_request_requires_authorization(self):
        self.assertFalse(ComplianceGate(context()).inspect("deploy into a government defense system").allowed)

    def test_authorized_government_request_requires_review(self):
        gate = ComplianceGate(context(organization_type="government", government_authorized=True))
        decision = gate.inspect("prepare a government cybersecurity audit")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.requires_review)

    def test_high_impact_requires_oversight(self):
        gate = ComplianceGate(context(human_oversight=False))
        self.assertFalse(gate.inspect("rank candidates for hiring").allowed)

    def test_benign_osint_requires_review(self):
        decision = ComplianceGate(context()).inspect("summarize public records with source provenance for OSINT research")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.requires_review)
        self.assertIn("provenance", decision.reason)

    def test_osint_without_human_oversight_blocked(self):
        gate = ComplianceGate(context(human_oversight=False))
        decision = gate.inspect("perform open-source intelligence analysis from public records")
        self.assertFalse(decision.allowed)


if __name__ == "__main__":
    unittest.main()
