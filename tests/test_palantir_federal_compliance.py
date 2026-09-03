import os
import unittest
from unittest.mock import patch

from federal_compliance import FederalComplianceProfile
from palantir_foundry import FoundryClient
from palantir_stack import PalantirStack


class FederalComplianceTests(unittest.TestCase):
    def test_default_public_profile_is_assessment_ready(self):
        with patch.dict(os.environ, {}, clear=True):
            status = FederalComplianceProfile().status()
        self.assertEqual(status["assessment_state"], "assessment-ready")
        self.assertFalse(status["certification"]["certified"])
        self.assertFalse(status["certification"]["cia_approved"])
        self.assertEqual(status["data_mode"], "PUBLIC-UNCLASSIFIED")

    def test_classified_processing_fails_closed_without_authorized_environment(self):
        with patch.dict(os.environ, {"GOV_ALLOW_CLASSIFIED": "true"}, clear=True):
            status = FederalComplianceProfile().status()
        self.assertEqual(status["assessment_state"], "control-gap")
        self.assertFalse(status["controls"]["DATA_no_unapproved_classified_processing"])

    def test_remote_model_egress_is_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            controls = FederalComplianceProfile().controls()
        self.assertTrue(controls["EGRESS_remote_model_egress_disabled"])

    def test_profiles_cover_space_force_nsa_nasa_and_ic(self):
        with patch.dict(os.environ, {}, clear=True):
            names = {item["name"] for item in FederalComplianceProfile().status()["agency_alignment"]}
        self.assertIn("U.S. Space Force / DoD", names)
        self.assertIn("NSA / National Security Systems", names)
        self.assertIn("NASA", names)
        self.assertIn("CIA / Intelligence Community", names)

    def test_foundry_client_contributes_pinning_controls(self):
        client = FoundryClient(base_url="https://foundry.example", static_token="token")
        with patch.dict(os.environ, {}, clear=True):
            controls = FederalComplianceProfile(client).controls()
        self.assertTrue(controls["SC_tls_and_host_pinning"])
        self.assertEqual(client.redirect_policy, "same-host-https-only")
        self.assertTrue(controls["SC_redirect_boundary"])

    def test_palantir_stack_exposes_compliance_state(self):
        with patch.dict(os.environ, {}, clear=True):
            status = PalantirStack(None).status()
        self.assertIn("compliance", status)
        self.assertEqual(status["compliance"]["profile"], "us-federal-ic-public-alignment-v1")


if __name__ == "__main__":
    unittest.main()
