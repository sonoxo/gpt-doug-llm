"""CL1 Mac stale-file repair: offline tests, no HTTP and no third-party packages."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "cl1_body_terminal.py"
INSTALLER = ROOT / "scripts" / "install_cl1_terminal.py"
spec = importlib.util.spec_from_file_location("cl1_installer", INSTALLER)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CL1InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = SOURCE.read_bytes()

    def test_local_current_source_has_expected_release_and_ontology(self):
        sha = installer._validate_source(self.source_bytes)
        self.assertEqual(len(sha), 64)
        self.assertEqual(installer.RELEASE, "2026.11.09-terminal.4")

    def test_actual_commands_work_before_update(self):
        result = installer.verify_candidate(SOURCE)
        self.assertGreaterEqual(result["entities"], 19)
        self.assertEqual(result["relationships"], result["entities"] - 1)
        self.assertEqual(result["joint_tested"], "cl1:segment/left_forearm")
        self.assertEqual(result["display_tested"], "SKELETON | 01 | BONE")
        self.assertFalse(result["hardware_connected"])

    def test_old_install_is_backed_up_and_replaced_only_after_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cl1_body_terminal.py"
            legacy = b"print('FUSION | CYAN')\n"
            destination.write_bytes(legacy)
            result = installer.install(
                destination, fetcher=lambda: self.source_bytes,
                verifier=installer.verify_candidate,
            )
            self.assertTrue(result["changed"])
            self.assertEqual(destination.read_bytes(), self.source_bytes)
            self.assertEqual(Path(result["backup"]).read_bytes(), legacy)
            self.assertEqual(result["entities"], 19)

    def test_repeated_install_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cl1_body_terminal.py"
            destination.write_bytes(self.source_bytes)
            result = installer.install(
                destination, fetcher=lambda: self.source_bytes,
                verifier=installer.verify_candidate,
            )
            self.assertFalse(result["changed"])
            self.assertIsNone(result["backup"])

    def test_fixed_https_download_requires_expected_source(self):
        class Response:
            status = 200
            def read(self, max_size):
                self.max_size = max_size
                return self_payload
        class Connection:
            def __init__(self):
                self.path = None
                self.closed = False
            def request(self, method, path, headers=None):
                self.path = (method, path)
            def getresponse(self):
                return Response()
            def close(self):
                self.closed = True
        self_payload = self.source_bytes
        connection = Connection()
        with patch.object(installer, "HTTPSConnection", return_value=connection) as tls:
            result = installer.fetch_official_source()
        self.assertEqual(result, self.source_bytes)
        self.assertEqual(connection.path[0], "GET")
        self.assertEqual(connection.path[1], "/sonoxo/gpt-doug-llm/main/scripts/cl1_body_terminal.py")
        self.assertTrue(connection.closed)
        self.assertEqual(tls.call_args.args, ("raw.githubusercontent.com",))

    def test_http_redirect_is_rejected_without_following(self):
        class Response:
            status = 302
        class Connection:
            def request(self, *args, **kwargs):
                pass
            def getresponse(self):
                return Response()
            def close(self):
                self.closed = True
        connection = Connection()
        with patch.object(installer, "HTTPSConnection", return_value=connection):
            with self.assertRaisesRegex(OSError, "not HTTP 200"):
                installer.fetch_official_source()
        self.assertTrue(connection.closed)

    def test_bad_download_preserves_existing_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cl1_body_terminal.py"
            destination.write_text("legacy user code\n")
            with self.assertRaises(ValueError):
                installer.install(destination, fetcher=lambda: b"not complete")
            self.assertEqual(destination.read_text(), "legacy user code\n")
            self.assertEqual(list(Path(directory).glob(".cl1-verified-*")), [])

    def test_failing_candidate_does_not_replace_old_renderer(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "cl1_body_terminal.py"
            destination.write_text("original\n")
            with self.assertRaisesRegex(ValueError, "synthetic functional failure"):
                installer.install(
                    destination,
                    fetcher=lambda: self.source_bytes,
                    verifier=lambda _: (_ for _ in ()).throw(
                        ValueError("synthetic functional failure")
                    ),
                )
            self.assertEqual(destination.read_text(), "original\n")
            self.assertEqual(list(Path(directory).glob(".cl1-verified-*")), [])

    def test_refuses_symlink_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "personal.txt"
            original.write_text("private")
            destination = Path(directory) / "cl1_body_terminal.py"
            destination.symlink_to(original)
            with self.assertRaisesRegex(ValueError, "symlink"):
                installer.install(destination, fetcher=lambda: self.source_bytes)
            self.assertEqual(original.read_text(), "private")

    def test_main_launches_verified_bone_skeleton(self):
        result = {
            "version": installer.RELEASE, "entities": 19,
            "path": "/tmp/cl1_body_terminal.py",
            "sha256": "a" * 64, "backup": None,
        }
        out = io.StringIO()
        with patch.object(installer, "install", return_value=result), patch.object(
            installer.subprocess, "call", return_value=0
        ) as run:
            with contextlib.redirect_stdout(out):
                self.assertEqual(installer.main([]), 0)
        self.assertEqual(
            run.call_args.args[0],
            [sys.executable, "/tmp/cl1_body_terminal.py", "--mode", "skeleton",
             "--color", "bone", "--no-spin"],
        )
        self.assertIn("CL1 VERIFIED", out.getvalue())

    def test_main_inspect_passes_through_and_install_only_never_executes(self):
        result = {
            "version": installer.RELEASE, "entities": 19,
            "path": "/tmp/cl1_body_terminal.py", "backup": None,
        }
        with patch.object(installer, "install", return_value=result), patch.object(
            installer.subprocess, "call", return_value=0
        ) as run:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--inspect", "left_forearm"]), 0)
            self.assertEqual(
                run.call_args.args[0],
                [sys.executable, "/tmp/cl1_body_terminal.py",
                 "--inspect", "left_forearm"],
            )
            run.reset_mock()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--install-only"]), 0)
            run.assert_not_called()

    def test_invalid_source_version_rejected(self):
        older = self.source_bytes.replace(installer.RELEASE.encode(), b"2025-old")
        with self.assertRaisesRegex(ValueError, "without the current ontology"):
            installer._validate_source(older)


if __name__ == "__main__":
    unittest.main()
