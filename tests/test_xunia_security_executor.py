import subprocess
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock

from xunia_security import Engagement, SecurityMode, Target, XuniaSecurityPlatform
from xunia_security_executor import AuthorizedToolExecutor, ExecutionPolicy


NOW = datetime(2026, 9, 1, 16, 0, tzinfo=timezone.utc)


def engagement():
    return Engagement(
        engagement_id="exec-demo-001",
        owner="security-owner",
        mode=SecurityMode.PENTEST,
        starts_at=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
        targets=(Target("url", "https://lab.example.test"),),
        allowed_checks=("service.discovery",),
        authorization_reference="AUTH-EXEC-001",
    )


class AuthorizedToolExecutorTests(unittest.TestCase):
    def executor(self, runner=None, resolver=None):
        return AuthorizedToolExecutor(
            policy=ExecutionPolicy(timeout_seconds=30, max_output_bytes=32),
            runner=runner or Mock(return_value=subprocess.CompletedProcess(["nmap"], 0, stdout=b"ok", stderr=b"")),
            binary_resolver=resolver or (lambda binary: f"/usr/bin/{binary}"),
            clock=lambda: NOW,
        )

    def test_authorized_step_runs_exact_argv_without_shell(self):
        platform = XuniaSecurityPlatform()
        e = engagement()
        step = platform.plan(e, NOW).steps[0]
        runner = Mock(return_value=subprocess.CompletedProcess(list(step.argv), 0, stdout=b"service open", stderr=b""))
        evidence = self.executor(runner=runner).execute(e, step)
        runner.assert_called_once_with(
            list(step.argv),
            shell=False,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(evidence.status, "COMPLETED")
        self.assertEqual(evidence.tool_id, "nmap")
        self.assertEqual(evidence.planned_evidence_id, step.evidence_id)

    def test_out_of_scope_step_never_reaches_runner(self):
        platform = XuniaSecurityPlatform()
        e = engagement()
        step = platform.plan(e, NOW).steps[0]
        out_of_scope = replace(step, target=Target("url", "https://other.example.test"))
        runner = Mock()
        with self.assertRaises(PermissionError):
            self.executor(runner=runner).execute(e, out_of_scope)
        runner.assert_not_called()

    def test_tampered_shell_command_never_reaches_runner(self):
        platform = XuniaSecurityPlatform()
        e = engagement()
        step = platform.plan(e, NOW).steps[0]
        tampered = replace(step, argv=("sh", "-c", "echo denied"))
        runner = Mock()
        with self.assertRaisesRegex(PermissionError, "COMMAND_INTEGRITY_CHECK_FAILED"):
            self.executor(runner=runner).execute(e, tampered)
        runner.assert_not_called()

    def test_missing_binary_never_reaches_runner(self):
        e = engagement()
        step = XuniaSecurityPlatform().plan(e, NOW).steps[0]
        runner = Mock()
        with self.assertRaisesRegex(FileNotFoundError, "SECURITY_BINARY_NOT_INSTALLED:nmap"):
            self.executor(runner=runner, resolver=lambda _binary: None).execute(e, step)
        runner.assert_not_called()

    def test_evidence_preview_is_bounded_but_hashes_full_output(self):
        e = engagement()
        step = XuniaSecurityPlatform().plan(e, NOW).steps[0]
        runner = Mock(return_value=subprocess.CompletedProcess(list(step.argv), 0, stdout=b"A" * 100, stderr=b"B" * 100))
        evidence = self.executor(runner=runner).execute(e, step)
        self.assertTrue(evidence.output_truncated)
        self.assertLessEqual(len(evidence.stdout_preview.encode()), 16)
        self.assertLessEqual(len(evidence.stderr_preview.encode()), 16)
        self.assertEqual(len(evidence.stdout_sha256), 64)
        self.assertEqual(len(evidence.stderr_sha256), 64)

    def test_timeout_returns_timeout_evidence(self):
        e = engagement()
        step = XuniaSecurityPlatform().plan(e, NOW).steps[0]
        runner = Mock(side_effect=subprocess.TimeoutExpired(list(step.argv), 30, output=b"partial", stderr=b"slow"))
        evidence = self.executor(runner=runner).execute(e, step)
        self.assertEqual(evidence.status, "TIMEOUT")
        self.assertEqual(evidence.returncode, 124)


if __name__ == "__main__":
    unittest.main()
