"""Strict operator-mounted stop-state regression tests.

Uses temporary directories and mock environment only. Does not activate any
real host's kill switch or require model/API credentials.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ai_killswitch as ks


class TestStrictStopState(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.mount = Path(self.temp.name) / "operator-mounted-stop"
        patch = mock.patch.dict(os.environ, {
            ks.STATE_DIRECTORY_ENV: str(self.mount),
            ks.REQUIRED_STOP_DIR_ENV: "1",
            ks.FORCE_STOP_ENV: "0",
        })
        patch.start()
        self.addCleanup(patch.stop)

    def test_missing_operator_mount_fails_closed(self):
        state = ks.status()
        self.assertTrue(state["stopped"])
        self.assertTrue(state["stop_directory_required"])
        self.assertEqual(state["reason"], "required_stop_directory_missing")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed("AI inference")

    def test_explicitly_provisioned_mount_allows_only_if_unlatched(self):
        self.mount.mkdir(mode=0o700)
        self.assertFalse(ks.status()["stopped"])
        ks.require_ai_allowed("AI inference")
        state = ks.emergency_stop("operator_test")
        self.assertTrue(state["stopped"])
        self.assertEqual(state["reason"], "operator_stop_latched")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed("AI inference")

    def test_missing_mount_after_stop_stays_stopped(self):
        self.mount.mkdir(mode=0o700)
        ks.emergency_stop()
        for child in self.mount.iterdir():
            child.unlink()
        self.mount.rmdir()
        self.assertEqual(ks.status()["reason"], "required_stop_directory_missing")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()

    def test_noninteractive_and_wrong_confirmation_never_rearm(self):
        self.mount.mkdir(mode=0o700)
        ks.emergency_stop()
        with mock.patch.object(ks.sys, "stdin") as stdin, mock.patch("builtins.input", return_value="wrong"):
            stdin.isatty.return_value = True
            with self.assertRaises(PermissionError):
                ks._resume_after_interactive_confirmation()
        self.assertTrue(ks.status()["stopped"])

    def test_cannot_rearm_without_required_mount(self):
        self.mount.mkdir(mode=0o700)
        ks.emergency_stop()
        for child in self.mount.iterdir():
            child.unlink()
        self.mount.rmdir()
        with mock.patch.object(ks.sys, "stdin") as stdin, mock.patch("builtins.input", return_value="REARM GPT-DOUG AI"):
            stdin.isatty.return_value = True
            with self.assertRaisesRegex(PermissionError, "unavailable"):
                ks._resume_after_interactive_confirmation()
        self.assertFalse(self.mount.exists())
        self.assertTrue(ks.status()["stopped"])

    def test_symlinked_directory_fails_closed(self):
        target = Path(self.temp.name) / "target"
        target.mkdir()
        self.mount.symlink_to(target, target_is_directory=True)
        self.assertEqual(ks.status()["reason"], "unsafe_stop_directory")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()

    def test_relative_operator_path_is_not_allowed(self):
        os.environ[ks.STATE_DIRECTORY_ENV] = "relative/stop-dir"
        self.assertEqual(ks.status()["reason"], "invalid_stop_configuration")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()

    def test_invalid_strict_setting_fails_closed(self):
        self.mount.mkdir(mode=0o700)
        os.environ[ks.REQUIRED_STOP_DIR_ENV] = "perhaps"
        self.assertTrue(ks.status()["stopped"])
        self.assertEqual(ks.status()["reason"], "invalid_required_stop_directory_configuration")

    def test_non_strict_initial_state_remains_backwards_compatible(self):
        os.environ[ks.REQUIRED_STOP_DIR_ENV] = "0"
        self.assertFalse(ks.status()["stopped"])
        self.assertFalse(ks.status()["stop_directory_required"])

    def test_host_stop_takes_precedence(self):
        os.environ[ks.FORCE_STOP_ENV] = "1"
        self.assertEqual(ks.status()["reason"], "host_enforced_stop")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()


if __name__ == "__main__":
    unittest.main()
