"""Regression tests for the human-latched GPT-Doug AI execution stop."""
from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import ai_killswitch as ks


class TestAIKillSwitch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch_dir = mock.patch.dict(os.environ, {
            ks.STATE_DIRECTORY_ENV: self.tmp.name,
            ks.FORCE_STOP_ENV: "0",
        })
        self.patch_dir.start()
        self.addCleanup(self.patch_dir.stop)

    def test_default_running_no_latch(self):
        self.assertFalse(ks.status()["stopped"])
        ks.require_ai_allowed("unit_test")

    def test_stop_persists_and_blocks_new_actions(self):
        first = ks.emergency_stop("integration-test")
        self.assertTrue(first["stopped"])
        self.assertEqual(first["reason"], "operator_stop_latched")
        second = ks.emergency_stop("retry")
        self.assertEqual(second["reason"], "operator_stop_latched")
        latch = Path(self.tmp.name) / ks.STOP_FILENAME
        self.assertTrue(latch.is_file())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(latch.stat().st_mode), 0o600)
        with self.assertRaisesRegex(ks.AIKillSwitchEngaged, "AI_KILLSWITCH_ENGAGED"):
            ks.require_ai_allowed("model request")
        self.assertEqual(len((Path(self.tmp.name)/"operator-audit.jsonl").read_text().splitlines()), 1)

    def test_host_override_blocks_even_without_file(self):
        os.environ[ks.FORCE_STOP_ENV] = "true"
        self.assertTrue(ks.status()["stopped"])
        self.assertEqual(ks.status()["reason"], "host_enforced_stop")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()

    def test_invalid_host_configuration_fails_closed(self):
        os.environ[ks.FORCE_STOP_ENV] = "maybe"
        self.assertEqual(ks.status()["reason"], "invalid_host_stop_configuration")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()

    def test_invalid_state_directory_fails_closed(self):
        path = Path(self.tmp.name) / "malicious"
        path.write_text("not a dir")
        os.environ[ks.STATE_DIRECTORY_ENV] = str(path)
        self.assertEqual(ks.status()["reason"], "unsafe_stop_directory")

    def test_symlinked_stop_file_fails_closed(self):
        target = Path(self.tmp.name)/"data"
        target.write_text("ignored")
        (Path(self.tmp.name)/ks.STOP_FILENAME).symlink_to(target)
        self.assertEqual(ks.status()["reason"], "invalid_stop_latch_type")
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ks.require_ai_allowed()

    def test_stream_stops_between_events_and_closes(self):
        closed = []
        def source():
            try:
                yield "first"
                yield "second"
            finally:
                closed.append(True)
        iterator = ks.guarded_stream(source())
        self.assertEqual(next(iterator), "first")
        ks.emergency_stop()
        with self.assertRaises(ks.AIKillSwitchEngaged):
            next(iterator)
        self.assertTrue(closed)

    def test_retry_sleep_interrupted(self):
        done = []
        def worker():
            try:
                ks.interruptible_sleep(3)
            except ks.AIKillSwitchEngaged:
                done.append(True)
        thread = threading.Thread(target=worker)
        thread.start()
        time.sleep(.05)
        ks.emergency_stop()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(done, [True])

    def test_no_noninteractive_rearm(self):
        ks.emergency_stop()
        with mock.patch.object(ks.sys, "stdin") as fake_stdin:
            fake_stdin.isatty.return_value = False
            with self.assertRaises(PermissionError):
                ks._resume_after_interactive_confirmation()
        self.assertTrue(ks.status()["stopped"])

    def test_interactive_rearm_is_explicit(self):
        ks.emergency_stop()
        with mock.patch.object(ks.sys, "stdin") as fake_stdin, mock.patch("builtins.input", return_value="wrong"):
            fake_stdin.isatty.return_value = True
            with self.assertRaises(PermissionError):
                ks._resume_after_interactive_confirmation()
        self.assertTrue(ks.status()["stopped"])
        with mock.patch.object(ks.sys, "stdin") as fake_stdin, mock.patch("builtins.input", return_value="REARM GPT-DOUG AI"):
            fake_stdin.isatty.return_value = True
            self.assertFalse(ks._resume_after_interactive_confirmation()["stopped"])

    def test_forced_stop_cannot_be_locally_rearmed(self):
        ks.emergency_stop()
        os.environ[ks.FORCE_STOP_ENV] = "on"
        with mock.patch.object(ks.sys, "stdin") as fake_stdin, mock.patch("builtins.input", return_value="REARM GPT-DOUG AI"):
            fake_stdin.isatty.return_value = True
            with self.assertRaisesRegex(PermissionError, "host-enforced"):
                ks._resume_after_interactive_confirmation()
        self.assertTrue(ks.status()["stopped"])

    def test_check_command_exit_code_and_stop_idempotence(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(ks.main(["check"]), 0)
        self.assertFalse(json.loads(buf.getvalue())["stopped"])
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(ks.main(["stop"]), 0)
            self.assertEqual(ks.main(["check"]), 3)
        self.assertTrue(json.loads(buf.getvalue().splitlines()[-1])["stopped"])


if __name__ == "__main__":
    unittest.main()
