"""Local-first realtime runtime for XUNIA security engagements.

The service is intentionally free to run: Python stdlib + the registered OSS security
binaries. It binds to loopback by default, persists jobs/events/evidence/findings in SQLite,
and executes only plans already authorized by xunia_security.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from xunia_findings import NormalizedFinding, normalize_evidence
from xunia_security import Engagement, SecurityMode, Target, XuniaSecurityPlatform
from xunia_security_executor import AuthorizedToolExecutor, ExecutionEvidence

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_DB = ".xunia/realtime.db"
MAX_GLOBAL_WORKERS = 8
TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def engagement_from_dict(data: dict[str, Any]) -> Engagement:
    if data.get("schemaVersion") != "xunia.security.engagement/v1":
        raise ValueError("UNSUPPORTED_ENGAGEMENT_SCHEMA")
    return Engagement(
        engagement_id=str(data["engagementId"]),
        owner=str(data["owner"]),
        mode=SecurityMode(str(data["mode"])),
        starts_at=_parse_dt(str(data["startsAt"])),
        ends_at=_parse_dt(str(data["endsAt"])),
        targets=tuple(Target(str(item["type"]), str(item["value"])) for item in data["targets"]),
        exclusions=tuple(Target(str(item["type"]), str(item["value"])) for item in data.get("exclusions", [])),
        allowed_checks=tuple(str(item) for item in data["allowedChecks"]),
        max_requests_per_second=int(data.get("maxRequestsPerSecond", 10)),
        max_concurrency=int(data.get("maxConcurrency", 4)),
        destructive_allowed=bool(data.get("destructiveAllowed", False)),
        authorization_reference=str(data["authorizationReference"]),
    )


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: set[queue.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        channel: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=256)
        with self._lock:
            self._subscribers.add(channel)
        return channel

    def unsubscribe(self, channel: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            self._subscribers.discard(channel)

    def publish(self, event: dict[str, Any]) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers)
        for channel in subscribers:
            try:
                channel.put_nowait(event)
            except queue.Full:
                pass


class RuntimeStore:
    def __init__(self, db_path: str = DEFAULT_DB) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    engagement_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    parent_job_id TEXT,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    step_order INTEGER NOT NULL,
                    tool_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    manifest_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT,
                    next_run_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    job_id TEXT NOT NULL,
                    tool_id TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    description TEXT NOT NULL,
                    remediation TEXT NOT NULL,
                    references_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    verified_at TEXT,
                    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS remediation_tasks (
                    id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'QUEUED',
                    recommendation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(finding_id) REFERENCES findings(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finding_id TEXT,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status, severity);
                CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);
                """
            )

    def create_job(self, job_id: str, manifest: dict[str, Any], parent_job_id: Optional[str] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs(id, engagement_id, status, manifest_json, created_at, parent_job_id) VALUES(?,?,?,?,?,?)",
                (job_id, manifest["engagementId"], "QUEUED", json.dumps(manifest, sort_keys=True), _iso(_utcnow()), parent_job_id),
            )

    def update_job(self, job_id: str, status: str, *, error: Optional[str] = None) -> None:
        now = _iso(_utcnow())
        fields = ["status = ?"]
        values: list[Any] = [status]
        if status == "RUNNING":
            fields.append("started_at = COALESCE(started_at, ?)")
            values.append(now)
        if status in TERMINAL_STATES:
            fields.append("finished_at = ?")
            values.append(now)
        if error is not None:
            fields.append("error = ?")
            values.append(error[:4000])
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values)

    def add_evidence(self, job_id: str, step_order: int, evidence: ExecutionEvidence) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO evidence(job_id, step_order, tool_id, target, status, evidence_json, created_at) VALUES(?,?,?,?,?,?,?)",
                (
                    job_id,
                    step_order,
                    evidence.tool_id,
                    evidence.target,
                    evidence.status,
                    json.dumps(asdict(evidence), sort_keys=True),
                    _iso(_utcnow()),
                ),
            )

    def add_findings(self, job_id: str, findings: list[NormalizedFinding]) -> list[dict[str, Any]]:
        now = _iso(_utcnow())
        persisted: list[dict[str, Any]] = []
        with self._connect() as conn:
            for finding in findings:
                existing = conn.execute(
                    "SELECT id, status FROM findings WHERE fingerprint = ?", (finding.fingerprint,)
                ).fetchone()
                finding_id = existing["id"] if existing else uuid.uuid4().hex
                if existing:
                    conn.execute(
                        """UPDATE findings
                        SET job_id=?, tool_id=?, severity=?, title=?, resource=?, description=?, remediation=?,
                            references_json=?, status='OPEN', last_seen_at=?, verified_at=NULL
                        WHERE id=?""",
                        (
                            job_id,
                            finding.tool_id,
                            finding.severity,
                            finding.title,
                            finding.resource,
                            finding.description,
                            finding.remediation,
                            json.dumps(list(finding.references)),
                            now,
                            finding_id,
                        ),
                    )
                else:
                    conn.execute(
                        """INSERT INTO findings(
                        id,fingerprint,job_id,tool_id,severity,title,resource,description,remediation,references_json,status,first_seen_at,last_seen_at
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,'OPEN',?,?)""",
                        (
                            finding_id,
                            finding.fingerprint,
                            job_id,
                            finding.tool_id,
                            finding.severity,
                            finding.title,
                            finding.resource,
                            finding.description,
                            finding.remediation,
                            json.dumps(list(finding.references)),
                            now,
                            now,
                        ),
                    )
                task_id = f"rem-{finding_id}"
                conn.execute(
                    """INSERT INTO remediation_tasks(id,finding_id,status,recommendation,created_at,updated_at)
                    VALUES(?,?,'QUEUED',?,?,?)
                    ON CONFLICT(finding_id) DO UPDATE SET
                      status=CASE WHEN remediation_tasks.status='DONE' THEN 'QUEUED' ELSE remediation_tasks.status END,
                      recommendation=excluded.recommendation,
                      updated_at=excluded.updated_at""",
                    (task_id, finding_id, finding.remediation, now, now),
                )
                persisted.append({"id": finding_id, **finding.to_dict(), "status": "OPEN"})
        return persisted

    def verify_parent_findings(self, parent_job_id: str, retest_job_id: str) -> list[dict[str, Any]]:
        now = _iso(_utcnow())
        with self._connect() as conn:
            parent_rows = conn.execute("SELECT * FROM findings WHERE job_id = ?", (parent_job_id,)).fetchall()
            retest_fingerprints = {
                row["fingerprint"]
                for row in conn.execute("SELECT fingerprint FROM findings WHERE job_id = ?", (retest_job_id,)).fetchall()
            }
            verified = []
            for row in parent_rows:
                if row["fingerprint"] in retest_fingerprints:
                    conn.execute("UPDATE findings SET status='OPEN', verified_at=NULL WHERE id=?", (row["id"],))
                    continue
                conn.execute(
                    "UPDATE findings SET status='VERIFIED', verified_at=?, last_seen_at=? WHERE id=?",
                    (now, now, row["id"]),
                )
                conn.execute(
                    "UPDATE remediation_tasks SET status='DONE', updated_at=? WHERE finding_id=?",
                    (now, row["id"]),
                )
                verified.append({"id": row["id"], "fingerprint": row["fingerprint"], "title": row["title"]})
        return verified

    def set_finding_status(self, finding_id: str, status: str) -> bool:
        if status not in {"OPEN", "IN_PROGRESS", "RESOLVED_PENDING_RETEST", "RETESTING", "VERIFIED", "DISMISSED"}:
            raise ValueError("INVALID_FINDING_STATUS")
        with self._connect() as conn:
            cursor = conn.execute("UPDATE findings SET status=? WHERE id=?", (status, finding_id))
            if cursor.rowcount and status in {"IN_PROGRESS", "RESOLVED_PENDING_RETEST", "RETESTING"}:
                conn.execute(
                    "UPDATE remediation_tasks SET status=?, updated_at=? WHERE finding_id=?",
                    ("IN_PROGRESS", _iso(_utcnow()), finding_id),
                )
            return bool(cursor.rowcount)

    def finding_source_job(self, finding_id: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute("SELECT job_id FROM findings WHERE id=?", (finding_id,)).fetchone()
        return str(row["job_id"]) if row else None

    def list_findings(self, limit: int = 200) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM findings ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, last_seen_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                **{key: row[key] for key in row.keys() if key != "references_json"},
                "references": json.loads(row["references_json"]),
            }
            for row in rows
        ]

    def list_remediations(self, limit: int = 200) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT r.*, f.title, f.severity, f.resource, f.status AS finding_status
                FROM remediation_tasks r JOIN findings f ON f.id=r.finding_id
                ORDER BY CASE f.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, r.updated_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_notification(self, finding_id: str, severity: str, title: str, message: str) -> dict[str, Any]:
        now = _iso(_utcnow())
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO notifications(finding_id,severity,title,message,created_at) VALUES(?,?,?,?,?)",
                (finding_id, severity, title[:500], message[:4000], now),
            )
        return {"id": cursor.lastrowid, "findingId": finding_id, "severity": severity, "title": title, "message": message, "createdAt": now}

    def list_notifications(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def add_event(self, event_type: str, payload: dict[str, Any], job_id: Optional[str] = None) -> dict[str, Any]:
        event = {"type": event_type, "jobId": job_id, "payload": payload, "createdAt": _iso(_utcnow())}
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events(job_id, event_type, payload_json, created_at) VALUES(?,?,?,?)",
                (job_id, event_type, json.dumps(payload, sort_keys=True), event["createdAt"]),
            )
            event["id"] = cursor.lastrowid
        return event

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            evidence_rows = conn.execute(
                "SELECT step_order, evidence_json FROM evidence WHERE job_id = ? ORDER BY step_order, id", (job_id,)
            ).fetchall()
        result = dict(row)
        result["manifest"] = json.loads(result.pop("manifest_json"))
        result["evidence"] = [json.loads(item["evidence_json"]) for item in evidence_rows]
        return result

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [
            {**{key: row[key] for key in row.keys() if key != "manifest_json"}, "manifest": json.loads(row["manifest_json"])}
            for row in rows
        ]

    def create_schedule(self, name: str, interval_seconds: int, manifest: dict[str, Any]) -> dict[str, Any]:
        if interval_seconds < 60:
            raise ValueError("SCHEDULE_INTERVAL_MINIMUM_60_SECONDS")
        if interval_seconds > 2_592_000:
            raise ValueError("SCHEDULE_INTERVAL_MAXIMUM_30_DAYS")
        schedule_id = uuid.uuid4().hex
        next_run_at = _iso(datetime.fromtimestamp(_utcnow().timestamp() + interval_seconds, tz=timezone.utc))
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO schedules(id,name,interval_seconds,manifest_json,enabled,next_run_at) VALUES(?,?,?,?,1,?)",
                (schedule_id, name[:200], interval_seconds, json.dumps(manifest, sort_keys=True), next_run_at),
            )
        return {"id": schedule_id, "name": name, "intervalSeconds": interval_seconds, "nextRunAt": next_run_at, "enabled": True}

    def due_schedules(self, now: datetime) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM schedules WHERE enabled=1 AND next_run_at<=? ORDER BY next_run_at", (_iso(now),)
            ).fetchall()

    def mark_schedule_run(self, schedule_id: str, interval_seconds: int, now: datetime) -> None:
        next_run = datetime.fromtimestamp(now.timestamp() + interval_seconds, tz=timezone.utc)
        with self._connect() as conn:
            conn.execute(
                "UPDATE schedules SET last_run_at=?, next_run_at=? WHERE id=?",
                (_iso(now), _iso(next_run), schedule_id),
            )


class RealtimeOrchestrator:
    def __init__(
        self,
        store: Optional[RuntimeStore] = None,
        platform: Optional[XuniaSecurityPlatform] = None,
        executor_factory: Callable[[], AuthorizedToolExecutor] = AuthorizedToolExecutor,
        global_workers: int = MAX_GLOBAL_WORKERS,
    ) -> None:
        if global_workers < 1 or global_workers > 32:
            raise ValueError("GLOBAL_WORKERS_OUT_OF_RANGE")
        self.store = store or RuntimeStore()
        self.platform = platform or XuniaSecurityPlatform()
        self.executor_factory = executor_factory
        self.global_workers = global_workers
        self.events = EventBus()
        self._job_pool = ThreadPoolExecutor(max_workers=global_workers, thread_name_prefix="xunia-job")
        self._global_slots = threading.Semaphore(global_workers)
        self._cancelled: set[str] = set()
        self._state_lock = threading.Lock()
        self._stop = threading.Event()
        self._scheduler = threading.Thread(target=self._scheduler_loop, name="xunia-scheduler", daemon=True)
        self._scheduler.start()

    def close(self) -> None:
        self._stop.set()
        self._job_pool.shutdown(wait=False, cancel_futures=True)

    def _emit(self, event_type: str, payload: dict[str, Any], job_id: Optional[str] = None) -> None:
        self.events.publish(self.store.add_event(event_type, payload, job_id))

    def submit(self, manifest: dict[str, Any], parent_job_id: Optional[str] = None) -> str:
        engagement = engagement_from_dict(manifest)
        now = _utcnow()
        engagement.validate(now)
        self.platform.plan(engagement, now)
        job_id = uuid.uuid4().hex
        self.store.create_job(job_id, manifest, parent_job_id)
        self._emit("job.queued", {"engagementId": engagement.engagement_id}, job_id)
        self._job_pool.submit(self._run_job, job_id, manifest, parent_job_id)
        return job_id

    def cancel(self, job_id: str) -> bool:
        job = self.store.get_job(job_id)
        if job is None or job["status"] in TERMINAL_STATES:
            return False
        with self._state_lock:
            self._cancelled.add(job_id)
        self.store.update_job(job_id, "CANCELLED")
        self._emit("job.cancelled", {}, job_id)
        return True

    def retest(self, job_id: str) -> str:
        job = self.store.get_job(job_id)
        if job is None:
            raise KeyError("JOB_NOT_FOUND")
        manifest = dict(job["manifest"])
        now = _utcnow()
        manifest["engagementId"] = f"{manifest['engagementId']}-retest-{int(now.timestamp())}"
        manifest["startsAt"] = _iso(now)
        manifest["endsAt"] = _iso(datetime.fromtimestamp(now.timestamp() + 3600, tz=timezone.utc))
        return self.submit(manifest, parent_job_id=job_id)

    def retest_finding(self, finding_id: str) -> str:
        source_job = self.store.finding_source_job(finding_id)
        if not source_job:
            raise KeyError("FINDING_NOT_FOUND")
        self.store.set_finding_status(finding_id, "RETESTING")
        return self.retest(source_job)

    def create_schedule(self, name: str, interval_seconds: int, manifest: dict[str, Any]) -> dict[str, Any]:
        engagement_from_dict(manifest).validate(_utcnow())
        return self.store.create_schedule(name, interval_seconds, manifest)

    def _is_cancelled(self, job_id: str) -> bool:
        with self._state_lock:
            return job_id in self._cancelled

    def _run_step(self, job_id: str, engagement: Engagement, step: Any) -> Optional[ExecutionEvidence]:
        if self._is_cancelled(job_id):
            return None
        with self._global_slots:
            if self._is_cancelled(job_id):
                return None
            self._emit("step.running", {"order": step.order, "tool": step.tool.id, "target": step.target.normalized()}, job_id)
            evidence = self.executor_factory().execute(engagement, step)
            self.store.add_evidence(job_id, step.order, evidence)
            persisted = self.store.add_findings(job_id, normalize_evidence(evidence))
            for finding in persisted:
                self._emit("finding.detected", finding, job_id)
                if finding["severity"] in {"critical", "high"}:
                    notification = self.store.add_notification(
                        finding["id"], finding["severity"], finding["title"], f"{finding['resource']} · {finding['remediation']}"
                    )
                    self._emit("notification.created", notification, job_id)
            self._emit("step.finished", {"order": step.order, "tool": step.tool.id, "status": evidence.status, "target": evidence.target, "findings": len(persisted)}, job_id)
            return evidence

    def _run_job(self, job_id: str, manifest: dict[str, Any], parent_job_id: Optional[str]) -> None:
        try:
            if self._is_cancelled(job_id):
                return
            engagement = engagement_from_dict(manifest)
            plan = self.platform.plan(engagement, _utcnow())
            if self._is_cancelled(job_id):
                return
            self.store.update_job(job_id, "RUNNING")
            self._emit("job.running", {"steps": len(plan.steps), "mode": engagement.mode.value}, job_id)
            max_workers = max(1, min(engagement.max_concurrency, self.global_workers, len(plan.steps) or 1))
            results: list[ExecutionEvidence] = []
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"xunia-step-{job_id[:6]}") as pool:
                futures = [pool.submit(self._run_step, job_id, engagement, step) for step in plan.steps]
                for future in as_completed(futures):
                    if self._is_cancelled(job_id):
                        continue
                    evidence = future.result()
                    if evidence is not None:
                        results.append(evidence)
            if self._is_cancelled(job_id):
                return
            failed = [item for item in results if item.status != "COMPLETED"]
            final_status = "FAILED" if failed else "COMPLETED"
            self.store.update_job(job_id, final_status)
            if parent_job_id:
                for verified in self.store.verify_parent_findings(parent_job_id, job_id):
                    self._emit("finding.verified", verified, job_id)
            self._emit("job.finished", {"status": final_status, "completed": len(results), "failed": len(failed), "findings": len(self.store.list_findings())}, job_id)
        except Exception as exc:  # noqa: BLE001
            if not self._is_cancelled(job_id):
                message = f"{type(exc).__name__}: {exc}"
                self.store.update_job(job_id, "FAILED", error=message)
                self._emit("job.failed", {"error": message}, job_id)

    def _scheduler_loop(self) -> None:
        while not self._stop.wait(1.0):
            now = _utcnow()
            for row in self.store.due_schedules(now):
                try:
                    manifest = json.loads(row["manifest_json"])
                    manifest["engagementId"] = f"{manifest['engagementId']}-scheduled-{int(now.timestamp())}"
                    manifest["startsAt"] = _iso(now)
                    manifest["endsAt"] = _iso(datetime.fromtimestamp(now.timestamp() + 3600, tz=timezone.utc))
                    job_id = self.submit(manifest)
                    self.store.mark_schedule_run(row["id"], int(row["interval_seconds"]), now)
                    self._emit("schedule.triggered", {"scheduleId": row["id"], "name": row["name"], "jobId": job_id})
                except Exception as exc:  # noqa: BLE001
                    self._emit("schedule.failed", {"scheduleId": row["id"], "error": str(exc)})


class RuntimeHttpHandler(BaseHTTPRequestHandler):
    server_version = "XUNIA-Realtime/1"
    orchestrator: RealtimeOrchestrator
    token: Optional[str] = None
    allow_remote = False

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.getenv("XUNIA_RUNTIME_QUIET") != "1":
            super().log_message(fmt, *args)

    def _authorized(self) -> bool:
        remote = self.client_address[0]
        loopback = remote in {"127.0.0.1", "::1"}
        if not loopback and not self.allow_remote:
            return False
        if self.token:
            return self.headers.get("Authorization") == f"Bearer {self.token}"
        return loopback

    def _json(self, status: int, payload: Any) -> None:
        encoded = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 2_000_000:
            raise ValueError("INVALID_REQUEST_BODY_SIZE")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON_OBJECT_REQUIRED")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "UNAUTHORIZED"})
        path = urlparse(self.path).path
        if path == "/health":
            return self._json(HTTPStatus.OK, {"status": "ok", "platform": "XUNIA_REALTIME_FREE", "workers": self.orchestrator.global_workers})
        if path == "/v1/jobs":
            return self._json(HTTPStatus.OK, {"jobs": self.orchestrator.store.list_jobs()})
        if path.startswith("/v1/jobs/"):
            job = self.orchestrator.store.get_job(path.rsplit("/", 1)[-1])
            return self._json(HTTPStatus.OK if job else HTTPStatus.NOT_FOUND, job or {"error": "JOB_NOT_FOUND"})
        if path == "/v1/findings":
            return self._json(HTTPStatus.OK, {"findings": self.orchestrator.store.list_findings()})
        if path == "/v1/remediations":
            return self._json(HTTPStatus.OK, {"remediations": self.orchestrator.store.list_remediations()})
        if path == "/v1/notifications":
            return self._json(HTTPStatus.OK, {"notifications": self.orchestrator.store.list_notifications()})
        if path == "/v1/events":
            return self._sse()
        return self._json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            return self._json(HTTPStatus.UNAUTHORIZED, {"error": "UNAUTHORIZED"})
        try:
            payload = self._body()
            path = urlparse(self.path).path
            if path == "/v1/jobs":
                return self._json(HTTPStatus.ACCEPTED, {"jobId": self.orchestrator.submit(payload.get("manifest", payload))})
            if path.endswith("/cancel") and path.startswith("/v1/jobs/"):
                return self._json(HTTPStatus.OK, {"cancelled": self.orchestrator.cancel(path.split("/")[-2])})
            if path.endswith("/retest") and path.startswith("/v1/jobs/"):
                return self._json(HTTPStatus.ACCEPTED, {"jobId": self.orchestrator.retest(path.split("/")[-2])})
            if path == "/v1/schedules":
                schedule = self.orchestrator.create_schedule(
                    str(payload.get("name", "XUNIA schedule")), int(payload["intervalSeconds"]), payload["manifest"]
                )
                return self._json(HTTPStatus.CREATED, schedule)
            if path.endswith("/resolve") and path.startswith("/v1/findings/"):
                finding_id = path.split("/")[-2]
                changed = self.orchestrator.store.set_finding_status(finding_id, "RESOLVED_PENDING_RETEST")
                return self._json(HTTPStatus.OK if changed else HTTPStatus.NOT_FOUND, {"updated": changed})
            if path.endswith("/retest") and path.startswith("/v1/findings/"):
                finding_id = path.split("/")[-2]
                return self._json(HTTPStatus.ACCEPTED, {"jobId": self.orchestrator.retest_finding(finding_id)})
            return self._json(HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
        except KeyError as exc:
            return self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except (ValueError, PermissionError, json.JSONDecodeError) as exc:
            return self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _sse(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        channel = self.orchestrator.events.subscribe()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    event = channel.get(timeout=15)
                    self.wfile.write(b"event: xunia\n")
                    self.wfile.write(b"data: " + json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n\n")
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.orchestrator.events.unsubscribe(channel)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, db_path: str = DEFAULT_DB, workers: int = MAX_GLOBAL_WORKERS) -> None:
    if host not in {"127.0.0.1", "::1", "localhost"} and os.getenv("XUNIA_RUNTIME_ALLOW_REMOTE") != "1":
        raise PermissionError("REMOTE_BIND_REQUIRES_XUNIA_RUNTIME_ALLOW_REMOTE=1")
    token = os.getenv("XUNIA_LOCAL_TOKEN")
    if host not in {"127.0.0.1", "::1", "localhost"} and not token:
        raise PermissionError("REMOTE_BIND_REQUIRES_XUNIA_LOCAL_TOKEN")
    orchestrator = RealtimeOrchestrator(store=RuntimeStore(db_path), global_workers=workers)
    RuntimeHttpHandler.orchestrator = orchestrator
    RuntimeHttpHandler.token = token
    RuntimeHttpHandler.allow_remote = os.getenv("XUNIA_RUNTIME_ALLOW_REMOTE") == "1"
    server = ThreadingHTTPServer((host, port), RuntimeHttpHandler)
    print(f"XUNIA realtime runtime listening on http://{host}:{port} with {workers} workers")
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        orchestrator.close()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the free local XUNIA realtime security runtime")
    parser.add_argument("--host", default=os.getenv("XUNIA_RUNTIME_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("XUNIA_RUNTIME_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--db", default=os.getenv("XUNIA_RUNTIME_DB", DEFAULT_DB))
    parser.add_argument("--workers", type=int, default=int(os.getenv("XUNIA_RUNTIME_WORKERS", str(MAX_GLOBAL_WORKERS))))
    args = parser.parse_args()
    serve(args.host, args.port, args.db, args.workers)


if __name__ == "__main__":
    main()
