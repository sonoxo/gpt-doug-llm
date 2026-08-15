import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from compliance import UserContext
from dev_terminal import DevTerminal


class DevTerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.auth = Mock()
        self.context = UserContext("US", "company", "developer", True, False, True)
        self.terminal = DevTerminal(self.auth, self.context, self.tmp.name, Path(self.tmp.name) / "audit.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def test_elevation_requires_totp_and_role(self):
        self.auth.authenticate.return_value = True
        self.assertTrue(self.terminal.elevate("123456"))
        user = UserContext("US", "company", "user", True, False, True)
        self.assertFalse(DevTerminal(self.auth, user, self.tmp.name, "audit").elevate("123456"))

    def test_rejects_arbitrary_shell(self):
        self.assertIn("DENIED", self.terminal.execute("rm -rf /"))
        self.assertIn("DENIED", self.terminal.execute("bash"))

    def test_config_does_not_expose_secrets(self):
        with patch.dict("os.environ", {"FOUNDRY_TOKEN": "secret", "GPT_DOUG_ROLE": "developer"}, clear=True):
            output = self.terminal.execute("config")
            self.assertNotIn("secret", output)
            self.assertNotIn("FOUNDRY_TOKEN", output)

    def test_status(self):
        self.assertIn("EUREKA 369 ACTIVE", self.terminal.execute("status"))


if __name__ == "__main__":
    unittest.main()
