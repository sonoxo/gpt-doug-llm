import json
import queue
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xunia_realtime_runtime import RealtimeOrchestrator, RuntimeStore
from xunia_security_executor import ExecutionEvidence

NOW = datetime.now(timezone.utc)


def manifest() -> dict:
    return {
        "schemaVersion": "xunia.security.engagement/v1",
        "engagementId": "runtime-test-001",
        "owner": "test-owner",
        "mode": "PENTEST",
        "startsAt": (NOW - timedelta(minutes=1)).isoformat(),
        "endsAt": (NOW + timedelta(hours=2)).isoformat(),
        "targets": [{"type": "url", "value": "https://lab.example.test"}],
        "exclusions": [],
        "allowedChecks": ["service.discovery", "web.templates", "web.baseline"],
        "maxRequestsPerSecond": 10,
        "maxConcurrency": 3,
        "destructiveAllowed": False,
        "authorizationReference": "AUTH-RUNTIME-TEST",
    }


class FakeExecutor:
    calls = []

    def execute(self, engagement, step):
        type(self).calls.append(step.tool.id)
        time.sleep(0.02)
        return ExecutionEvidence(
            engagement_id=engagement.engagement_id,
            planned_evidence_id=step.evidence_id,
            tool_id=step.tool.id,
            target_type=step.target.type,
            target=step.target.normalized(),
            argv=step.argv,
            started_at=NOW.isoformat(),
            finished_at=NOW.isoformat(),
            returncode=0,
            stdout_sha256="a" * 64,
            stderr_sha256="b" * 64,
            stdout_preview="ok",
            stderr_preview="",
            output_truncated=False,
            status="COMPLETED",
        )


class FindingExecutor(FakeExecutor):
    emit_finding = True

    def execute(self, engagement, step):
        evidence = super().execute(engagement, step)
        if step.tool.id != "nuclei" or not type(self).emit_finding:
            return evidence
        payload = {
            "template-id": "runtime-example",
            "matched-at": step.target.normalized(),
            "info": {"name": "Runtime example finding", "severity": "high"},
        }
        return ExecutionEvidence(
            **{
                **evidence.__dict__,
                "stdout_preview": json.dumps(payload),
            }
        )


class XuniaRealtimeRuntimeTests(unittest.TestCase):
    def setUp(self):
        FakeExecutor.calls = []
        FindingExecutor.calls = []
        FindingExecutor.emit_finding = True
        self.tempdir = tempfile.TemporaryDirectory()
        self.store = RuntimeStore(str(Path(self.tempdir.name) / "runtime.db"))
        self.runtime = RealtimeOrchestrator(
            store=self.store,
            executor_factory=FakeExecutor,
            global_workers=4,
        )

    def tearDown(self):
        self.runtime.close()
        self.tempdir.cleanup()

    def wait_for_terminal(self, job_id: str, timeout: float = 3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.store.get_job(job_id)
            if job and job["status"] in {"COMPLETED", "FAILED", "CANCELLED"}:
                return job
            time.sleep(0.02)
        self.fail(f"job {job_id} did not finish")

    def test_job_executes_authorized_steps_and_persists_evidence(self):
        job_id = self.runtime.submit(manifest())
        job = self.wait_for_terminal(job_id)
        self.assertEqual(job["status"], "COMPLETED")
        self.assertEqual(len(job["evidence"]), 3)
        self.assertCountEqual(FakeExecutor.calls, ["nmap", "nuclei", "zap-baseline"])

    def test_assess_mode_drops_safe_active_step(self):
        data = manifest()
        data["mode"] = "ASSESS"
        job = self.wait_for_terminal(self.runtime.submit(data))
        self.assertEqual(job["status"], "COMPLETED")
        self.assertNotIn("nuclei", FakeExecutor.calls)
        self.assertIn("nmap", FakeExecutor.calls)

    def test_retest_creates_child_job_with_fresh_window(self):
        first = self.runtime.submit(manifest())
        self.wait_for_terminal(first)
        retest = self.runtime.retest(first)
        child = self.wait_for_terminal(retest)
        self.assertEqual(child["parent_job_id"], first)
        self.assertIn("-retest-", child["engagement_id"])

    def test_cancel_marks_job_cancelled(self):
        job_id = self.runtime.submit(manifest())
        self.assertTrue(self.runtime.cancel(job_id))
        job = self.wait_for_terminal(job_id)
        self.assertEqual(job["status"], "CANCELLED")

    def test_interval_schedule_requires_at_least_sixty_seconds(self):
        with self.assertRaisesRegex(ValueError, "SCHEDULE_INTERVAL_MINIMUM_60_SECONDS"):
            self.runtime.create_schedule("too-fast", 5, manifest())
        schedule = self.runtime.create_schedule("minute", 60, manifest())
        self.assertTrue(schedule["enabled"])
        self.assertEqual(schedule["intervalSeconds"], 60)

    def test_event_bus_receives_live_job_events(self):
        channel = self.runtime.events.subscribe()
        try:
            job_id = self.runtime.submit(manifest())
            observed = []
            deadline = time.time() + 3
            while time.time() < deadline and "job.finished" not in observed:
                try:
                    event = channel.get(timeout=0.2)
                except queue.Empty:
                    continue
                if event.get("jobId") == job_id:
                    observed.append(event["type"])
            self.assertIn("job.queued", observed)
            self.assertIn("job.running", observed)
            self.assertIn("step.finished", observed)
            self.assertIn("job.finished", observed)
        finally:
            self.runtime.events.unsubscribe(channel)

    def test_high_finding_creates_remediation_and_notification(self):
        self.runtime.close()
        self.runtime = RealtimeOrchestrator(
            store=self.store,
            executor_factory=FindingExecutor,
            global_workers=4,
        )
        job_id = self.runtime.submit(manifest())
        self.wait_for_terminal(job_id)
        findings = self.store.list_findings()
        remediations = self.store.list_remediations()
        notifications = self.store.list_notifications()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "high")
        self.assertEqual(findings[0]["status"], "OPEN")
        self.assertEqual(len(remediations), 1)
        self.assertEqual(remediations[0]["status"], "QUEUED")
        self.assertEqual(len(notifications), 1)

    def test_retest_without_repeat_finding_verifies_original(self):
        self.runtime.close()
        self.runtime = RealtimeOrchestrator(
            store=self.store,
            executor_factory=FindingExecutor,
            global_workers=4,
        )
        first = self.runtime.submit(manifest())
        self.wait_for_terminal(first)
        finding = self.store.list_findings()[0]
        self.store.set_finding_status(finding["id"], "RESOLVED_PENDING_RETEST")
        FindingExecutor.emit_finding = False
        retest = self.runtime.retest(first)
        self.wait_for_terminal(retest)
        updated = next(item for item in self.store.list_findings() if item["id"] == finding["id"])
        self.assertEqual(updated["status"], "VERIFIED")
        self.assertEqual(self.store.list_remediations()[0]["status"], "DONE")


if __name__ == "__main__":
    unittest.main()
