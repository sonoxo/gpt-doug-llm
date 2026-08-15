import os
import unittest
from unittest.mock import patch

from foundry_guard import FoundrySecuritySink


class FoundryGuardTests(unittest.TestCase):
    def test_disabled_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(FoundrySecuritySink.from_environment())

    def test_rejects_plain_http(self):
        env = {"FOUNDRY_SECURITY_ENDPOINT": "http://foundry.example/events", "FOUNDRY_TOKEN": "token"}
        with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
            FoundrySecuritySink.from_environment()

    def test_rejects_non_allowlisted_host(self):
        env = {"FOUNDRY_SECURITY_ENDPOINT": "https://evil.example/events", "FOUNDRY_ALLOWED_HOST": "foundry.example", "FOUNDRY_TOKEN": "token"}
        with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
            FoundrySecuritySink.from_environment()

    def test_accepts_allowlisted_https(self):
        env = {"FOUNDRY_SECURITY_ENDPOINT": "https://foundry.example/events", "FOUNDRY_ALLOWED_HOST": "foundry.example", "FOUNDRY_TOKEN": "token"}
        with patch.dict(os.environ, env, clear=True):
            self.assertIsNotNone(FoundrySecuritySink.from_environment())


if __name__ == "__main__":
    unittest.main()
