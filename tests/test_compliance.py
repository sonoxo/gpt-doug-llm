import unittest

from compliance import ComplianceGate, UserContext


def context(**changes):
    values = dict(
        jurisdiction="US",
        organization_type="individual",
        role="user",
        age_verified=True,
        government_authorized=False,
        human_oversight=True,
    )
    values.update(changes)
    return UserContext(**values)


class ComplianceTests(unittest.TestCase):
    def test_normal_build_request_allowed(self):
        self.assertTrue(ComplianceGate(context()).inspect("build a calendar").allowed)

    def test_autonomous_targeting_blocked(self):
        self.assertFalse(ComplianceGate(context()).inspect("create autonomous military targeting").allowed)
        self.assertFalse(ComplianceGate(context()).inspect("automate weapon targeting").allowed)
        self.assertFalse(ComplianceGate(context()).inspect("autonomous drone target selection").allowed)

    def test_normalizes_unicode_confusables(self):
        self.assertFalse(ComplianceGate(context()).inspect("infer a person's rаce").allowed)

    def test_government_request_requires_authorization(self):
        self.assertFalse(ComplianceGate(context()).inspect("deploy into a government defense system").allowed)

    def test_authorized_government_request_still_requires_system_boundary(self):
        gate = ComplianceGate(context(organization_type="government", government_authorized=True))
        self.assertFalse(gate.inspect("prepare a government cybersecurity audit").allowed)

    def test_authorized_government_profile_requires_review(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            compliance_profile="federal",
        ))
        decision = gate.inspect("prepare a government cybersecurity audit")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.requires_review)
        self.assertIn("NIST-RMF", decision.control_ids)

    def test_high_impact_requires_oversight(self):
        gate = ComplianceGate(context(human_oversight=False))
        self.assertFalse(gate.inspect("rank candidates for hiring").allowed)

    def test_top_secret_fails_closed_without_personnel_and_facility_controls(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            classification_ceiling="TOP_SECRET",
        ))
        decision = gate.inspect("process TOP SECRET material")
        self.assertFalse(decision.allowed)
        self.assertIn("eligibility", decision.reason)

    def test_top_secret_authorized_path_requires_recorded_review(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            personnel_eligible=True,
            need_to_know=True,
            approved_classified_facility=True,
            classification_ceiling="TOP_SECRET",
            compliance_profile="ic",
        ))
        decision = gate.inspect("process TOP SECRET material")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.requires_review)
        self.assertIn("ICD-503", decision.control_ids)

    def test_sci_requires_explicit_compartment_authorization(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            personnel_eligible=True,
            need_to_know=True,
            approved_classified_facility=True,
            classification_ceiling="TS_SCI",
            compliance_profile="ic",
        ))
        self.assertFalse(gate.inspect("handle TS/SCI material").allowed)

    def test_sci_authorized_path_requires_review(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            personnel_eligible=True,
            need_to_know=True,
            sci_access_authorized=True,
            approved_classified_facility=True,
            classification_ceiling="TS_SCI",
            compliance_profile="ic",
        ))
        decision = gate.inspect("handle TS/SCI material")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.requires_review)

    def test_cji_fails_closed_without_cjis_controls(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            compliance_profile="cjis",
        ))
        self.assertFalse(gate.inspect("process CJI records").allowed)

    def test_cji_authorized_path_requires_mfa_encryption_audit_and_ir(self):
        gate = ComplianceGate(context(
            organization_type="government",
            government_authorized=True,
            system_authorized=True,
            approved_system_boundary=True,
            audit_enforced=True,
            cji_authorized=True,
            mfa_enforced=True,
            encryption_enforced=True,
            incident_response_ready=True,
            compliance_profile="cjis",
        ))
        decision = gate.inspect("process CJI records")
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.requires_review)
        self.assertIn("CJIS-5.9.5", decision.control_ids)


if __name__ == "__main__":
    unittest.main()
