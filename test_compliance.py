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


if __name__ == "__main__":
    unittest.main()
