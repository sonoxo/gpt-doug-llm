import os
import unittest
from unittest.mock import patch

from auth_gate import ThreeFactorGate, VerifiedIdentity, totp


SECRET = "JBSWY3DPEHPK3PXP"


class AuthGateTests(unittest.TestCase):
    def test_accepts_verified_business_identity(self):
        env = {"GPT_DOUG_VERIFIED_BUSINESS_EMAIL": "doug@sonoxo.com", "GPT_DOUG_ALLOWED_EMAIL_DOMAINS": "sonoxo.com", "GPT_DOUG_VERIFIED_PHONE": "+12125550123", "GPT_DOUG_TOTP_SECRET": SECRET}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(VerifiedIdentity.from_environment().telephone, "+12125550123")

    def test_rejects_consumer_email(self):
        env = {"GPT_DOUG_VERIFIED_BUSINESS_EMAIL": "doug@gmail.com", "GPT_DOUG_VERIFIED_PHONE": "+12125550123", "GPT_DOUG_TOTP_SECRET": SECRET}
        with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
            VerifiedIdentity.from_environment()

    def test_rejects_invalid_phone(self):
        env = {"GPT_DOUG_VERIFIED_BUSINESS_EMAIL": "doug@sonoxo.com", "GPT_DOUG_VERIFIED_PHONE": "2125550123", "GPT_DOUG_TOTP_SECRET": SECRET}
        with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
            VerifiedIdentity.from_environment()

    def test_totp_accepts_current_window(self):
        identity = VerifiedIdentity("doug@sonoxo.com", "+12125550123", SECRET)
        gate = ThreeFactorGate(identity)
        moment = 1_700_000_000
        self.assertTrue(gate.verify_totp(totp(SECRET, moment), moment))


if __name__ == "__main__":
    unittest.main()
