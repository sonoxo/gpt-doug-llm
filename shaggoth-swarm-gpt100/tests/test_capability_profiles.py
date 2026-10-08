import os
import unittest
from unittest.mock import patch

from shaggoth_swarm.capabilities import ALL_SUPPORTED_CAPABILITIES, PROFILES
from shaggoth_swarm.policy import CapabilityPolicy


class CapabilityPolicyTests(unittest.TestCase):
    def test_full_authorized_profile_contains_every_supported_capability(self):
        self.assertEqual(PROFILES["full-authorized"], ALL_SUPPORTED_CAPABILITIES)

    def test_environment_profile_can_enable_full_catalog(self):
        with patch.dict(os.environ, {"SHAGGOTH_CAPABILITY_PROFILE": "full-authorized"}, clear=False):
            policy = CapabilityPolicy.from_env()
        self.assertEqual(policy.allowed, ALL_SUPPORTED_CAPABILITIES)

    def test_denies_can_remove_capabilities_from_profile(self):
        with patch.dict(
            os.environ,
            {
                "SHAGGOTH_CAPABILITY_PROFILE": "full-authorized",
                "SHAGGOTH_DENY_CAPABILITIES": "process.run,http.write",
            },
            clear=False,
        ):
            policy = CapabilityPolicy.from_env()
        self.assertNotIn("process.run", policy.allowed)
        self.assertNotIn("http.write", policy.allowed)

    def test_scopes_are_explicit(self):
        policy = CapabilityPolicy(allowed=frozenset({"github.write"}))
        policy.grant_scope("github.write", frozenset({"sonoxo/gpt-doug-llm"}))
        policy.require_scope("github.write", "sonoxo/gpt-doug-llm")
        with self.assertRaises(PermissionError):
            policy.require_scope("github.write", "someone/else")

    def test_unknown_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            CapabilityPolicy(allowed=frozenset({"magic.root"}))


if __name__ == "__main__":
    unittest.main()
