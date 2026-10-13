"""Safe offline ENOSPC recovery and disk preflight contract tests."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import disk


class DiskRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.checkout = self.root / "osiris-ui"
        self.checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(self.checkout)], check=True)
        subprocess.run(["git", "-C", str(self.checkout), "remote", "add",
                        "origin", disk.OFFICIAL_ORIGIN], check=True)
        (self.checkout / "LICENSE").write_text("MIT License", encoding="utf-8")
        (self.checkout / "package-lock.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_preflight_rejects_low_space_without_removing_files(self):
        marker = self.checkout / "important-file.txt"
        marker.write_text("KEEP", encoding="utf-8")
        with patch.object(disk, "free_mb", return_value=250):
            with redirect_stderr(io.StringIO()) as out:
                result = disk.preflight(self.checkout)
        self.assertFalse(result["enough_free_space"])
        self.assertIn("BEFORE npm ci", out.getvalue())
        self.assertEqual(marker.read_text(), "KEEP")

    def test_preflight_accepts_ample_space(self):
        with patch.object(disk, "free_mb", return_value=6000):
            with redirect_stdout(io.StringIO()):
                result = disk.preflight(self.checkout, 4096)
        self.assertTrue(result["enough_free_space"])

    def test_repair_removes_only_verified_osiris_dependencies(self):
        modules = self.checkout / "node_modules"
        modules.mkdir()
        (modules / "half-extracted.txt").write_text("broken")
        unrelated = self.root / "unrelated-node_modules"
        unrelated.mkdir()
        (unrelated / "keep.txt").write_text("unrelated")
        (self.checkout / "project-data.txt").write_text("keep")
        with patch.object(disk, "urlopen", side_effect=URLError("not running")):
            with redirect_stdout(io.StringIO()):
                result = disk.repair(self.checkout)
        self.assertTrue(result["node_modules_removed"])
        self.assertFalse(result["npm_cache_cleared"])
        self.assertFalse(modules.exists())
        self.assertEqual((unrelated / "keep.txt").read_text(), "unrelated")
        self.assertEqual((self.checkout / "project-data.txt").read_text(), "keep")

    def test_repair_refuses_unrelated_origin(self):
        subprocess.run(["git", "-C", str(self.checkout), "remote",
                        "set-url", "origin", "https://github.com/other/repo.git"], check=True)
        modules = self.checkout / "node_modules"
        modules.mkdir()
        with self.assertRaisesRegex(ValueError, "unexpected Git remote"):
            disk.repair(self.checkout)
        self.assertTrue(modules.exists())

    def test_repair_refuses_symlinked_modules(self):
        target = self.root / "do-not-touch"
        target.mkdir()
        (target / "private.txt").write_text("safe")
        (self.checkout / "node_modules").symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            disk.repair(self.checkout)
        self.assertEqual((target / "private.txt").read_text(), "safe")

    def test_recovery_check_from_unrelated_directory_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as outside:
            completed = subprocess.run(
                ["sh", str(HERE / "recover.sh"), "--check"],
                cwd=outside, env={**os.environ, "OSIRIS_WORKTREE": str(self.checkout)},
                capture_output=True, text=True, timeout=12,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("npm's shared", completed.stdout)
        self.assertTrue((self.checkout / "LICENSE").exists())


if __name__ == "__main__":
    unittest.main()
