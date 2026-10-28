"""Offline tests for the guarded Devin integration boundary."""
import os
import unittest
from unittest.mock import patch

from adapter import build_request


class AdapterTests(unittest.TestCase):
    def test_missing_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DEVIN_API_KEY is required"):
                build_request("test", "prompt")

    def test_request_is_not_sent(self):
        with patch.dict(os.environ, {"DEVIN_API_KEY": "placeholder"}, clear=True):
            result = build_request("  title  ", "  prompt  ")
        self.assertEqual(result["status"], "prepared_not_sent")
        self.assertEqual(result["title"], "title")
        self.assertEqual(result["prompt"], "prompt")


if __name__ == "__main__":
    unittest.main()
