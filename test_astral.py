import base64
import os
import unittest
from unittest.mock import Mock, patch

from astral import AstralConfig, AstralGate
from auth_gate import VerifiedIdentity


class AstralTests(unittest.TestCase):
    def env(self):
        return {
            "ASTRAL_SECURITY_OFFICER_EMAIL": "security@sonoxo.com",
            "ASTRAL_SECURITY_OFFICER_PHONE": "+12125550124",
            "ASTRAL_SECURITY_OFFICER_TOTP_SECRET": "JBSWY3DPEHPK3PXP",
            "ASTRAL_AUDIT_HMAC_KEY": base64.b64encode(b"x" * 32).decode(),
        }

    def test_requires_independent_officer(self):
        primary = VerifiedIdentity("security@sonoxo.com", "+12125550124", "JBSWY3DPEHPK3PXP")
        with patch.dict(os.environ, self.env(), clear=True), self.assertRaises(ValueError):
            AstralConfig.from_environment(primary)

    def test_rejects_short_audit_key(self):
        env = self.env(); env["ASTRAL_AUDIT_HMAC_KEY"] = base64.b64encode(b"short").decode()
        primary = VerifiedIdentity("dev@sonoxo.com", "+12125550123", "JBSWY3DPEHPK3PXP")
        with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
            AstralConfig.from_environment(primary)

    def test_two_person_authorization(self):
        primary_identity = VerifiedIdentity("dev@sonoxo.com", "+12125550123", "JBSWY3DPEHPK3PXP")
        with patch.dict(os.environ, self.env(), clear=True):
            config = AstralConfig.from_environment(primary_identity)
        primary = Mock(); primary.authenticate.return_value = True
        gate = AstralGate(config, primary)
        gate.officer_gate.authenticate = Mock(return_value=True)
        self.assertTrue(gate.authorize("111111", "222222"))

    def test_locks_after_five_failures(self):
        primary_identity = VerifiedIdentity("dev@sonoxo.com", "+12125550123", "JBSWY3DPEHPK3PXP")
        with patch.dict(os.environ, self.env(), clear=True):
            config = AstralConfig.from_environment(primary_identity)
        primary = Mock(); primary.authenticate.return_value = False
        gate = AstralGate(config, primary)
        for _ in range(5): self.assertFalse(gate.authorize("bad", "bad", now=1000))
        primary.authenticate.return_value = True
        self.assertFalse(gate.authorize("good", "good", now=1001))


if __name__ == "__main__":
    unittest.main()
