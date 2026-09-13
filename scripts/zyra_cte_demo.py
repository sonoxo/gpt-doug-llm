#!/usr/bin/env python3
"""Loopback-only ZYRA-CTE government/hackathon demonstration server."""

from __future__ import annotations

import argparse
import json
import pathlib
import threading
import time
import urllib.parse
import uuid
import webbrowser
from copy import deepcopy
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from research_lab.approval import digest
from research_lab.cte import (
    CounterfactualTransactionEngine,
    ExecutionJournal,
    ProposedTransition,
    ReceiptAuthorizer,
    StateSnapshot,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "zyra-cte-demo"
DEFAULT_STATE_ROOT = (
    pathlib.Path.home()
    / ".config"
    / "gpt-doug"
    / "zyra-cte-demo"
)


class DemoController:
    """Synthetic CTE scenario used by the local visual showcase."""

    def __init__(self, state_root=DEFAULT_STATE_ROOT):
        self.root = pathlib.Path(state_root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.approval_database = self.root / "approvals.sqlite3"
        self.journal_database = self.root / "journal.sqlite3"

        self.approver = "demo-human-reviewer"
        self.engine = CounterfactualTransactionEngine()
        self._lock = threading.RLock()

        self._token = None
        self._receipt_fingerprint = None
        self._new_attempt()

    def _new_attempt(self):
        self.attempt_id = "demo-" + uuid.uuid4().hex[:12]

    @property
    def state_snapshot(self):
        return StateSnapshot(
            version="demo-ontology-v1",
            objects={
                "service": {
                    "name": "Emergency Communications Gateway",
                    "status": "ONLINE",
                    "version": "2.3.9",
                    "environment": "SYNTHETIC-DEMO",
                },
                "redundancy": {
                    "status": "READY",
                    "channels": 3,
                },
            },
        )

    @property
    def transition(self):
        return ProposedTransition(
            transition_id="demo-emergency-comms-update",
            actor="gpt-doug",
            changes={
                "service": {
                    "name": "Emergency Communications Gateway",
                    "status": "MAINTENANCE",
                    "version": "2.4.0",
                    "environment": "SYNTHETIC-DEMO",
                },
            },
            required_policy="policy-demo-v1",
            requires_human_approval=True,
        )

    @property
    def code_versions(self):
        return {
            "cte-engine": digest("zyra-cte-demo-code-v1"),
        }

    @property
    def data_versions(self):
        return {
            "ontology-schema": digest("zyra-cte-demo-schema-v1"),
        }

    @property
    def policy_versions(self):
        return {
            "policy-demo-v1": digest("zyra-cte-demo-policy-v1"),
        }

    def _authorizer(self):
        return ReceiptAuthorizer(
            str(self.approval_database),
            {self.approver},
        )

    def _journal(self):
        return ExecutionJournal(str(self.journal_database))

    def _journal_payload(self):
        if not self.journal_database.exists():
            return None, []

        journal = self._journal()

        try:
            attempt = journal.get(self.attempt_id)

            events = (
                [
                    asdict(event)
                    for event in journal.events(self.attempt_id)
                ]
                if attempt is not None
                else []
            )

            return (
                asdict(attempt)
                if attempt is not None
                else None,
                events,
            )
        finally:
            journal.close()

    def state(self):
        with self._lock:
            attempt, events = self._journal_payload()

            return {
                "schema": "zyra.cte.demo.v1",
                "classification": "UNCLASSIFIED // SYNTHETIC DEMO",
                "synthetic_only": True,
                "external_mutation": False,
                "human_control": True,
                "attempt_id": self.attempt_id,
                "scenario": {
                    "title": "Emergency Communications Update",
                    "description": (
                        "A synthetic government communications service "
                        "receives a proposed software update."
                    ),
                    "state": asdict(self.state_snapshot),
                    "transition": asdict(self.transition),
                },
                "receipt": {
                    "issued": self._token is not None,
                    "fingerprint": self._receipt_fingerprint,
                    "token_exposed_to_browser": False,
                },
                "attempt": attempt,
                "events": events,
            }

    def propose(self):
        with self._lock:
            journal = self._journal()
            authorizer = self._authorizer()

            try:
                attempt = authorizer.begin_attempt(
                    journal,
                    self.attempt_id,
                    self.state_snapshot,
                    self.transition,
                    self.code_versions,
                    self.data_versions,
                    self.policy_versions,
                    int(time.time()),
                )
            finally:
                authorizer.close()
                journal.close()

            return {
                "ok": True,
                "attempt": asdict(attempt),
                "external_mutation": False,
            }

    def preview(self):
        with self._lock:
            self.propose()

            branch = self.engine.fork(
                self.state_snapshot,
                self.transition,
            )

            simulation = self.engine.simulate(
                branch,
                self.transition,
            )

            return {
                "ok": True,
                "branch_id": branch.branch_id,
                "base_version": branch.base_version,
                "counterfactual_state": branch.objects,
                "simulation": {
                    "allowed": simulation.allowed,
                    "reasons": simulation.reasons,
                    "expected_state": simulation.expected_state,
                    "expected_state_digest": digest(
                        simulation.expected_state
                    ),
                },
                "real_state_mutated": False,
            }

    def authorize(self):
        with self._lock:
            self.propose()

            if self._token is not None:
                return {
                    "ok": True,
                    "receipt_issued": True,
                    "receipt_fingerprint": (
                        self._receipt_fingerprint
                    ),
                    "token_exposed_to_browser": False,
                }

            authorizer = self._authorizer()

            try:
                now = int(time.time())

                self._token = authorizer.issue(
                    self.state_snapshot,
                    self.transition,
                    self.code_versions,
                    self.data_versions,
                    self.policy_versions,
                    self.approver,
                    now,
                    ttl=600,
                )
            finally:
                authorizer.close()

            self._receipt_fingerprint = digest(
                self._token
            )[:16]

            return {
                "ok": True,
                "receipt_issued": True,
                "receipt_fingerprint": (
                    self._receipt_fingerprint
                ),
                "approver": self.approver,
                "ttl_seconds": 600,
                "token_exposed_to_browser": False,
            }

    def execute(self, drift=False):
        with self._lock:
            if self._token is None:
                raise ValueError(
                    "human authorization receipt is required"
                )

            observed_override = None

            if drift:
                branch = self.engine.fork(
                    self.state_snapshot,
                    self.transition,
                )

                simulation = self.engine.simulate(
                    branch,
                    self.transition,
                )

                observed_override = deepcopy(
                    simulation.expected_state
                )

                observed_override["service"]["status"] = (
                    "DEGRADED"
                )

            journal = self._journal()
            authorizer = self._authorizer()

            try:
                result = authorizer.execute_durable(
                    journal,
                    self.attempt_id,
                    self._token,
                    self.state_snapshot,
                    self.transition,
                    self.code_versions,
                    self.data_versions,
                    self.policy_versions,
                    int(time.time()),
                    observed_override=observed_override,
                )

                attempt = journal.get(self.attempt_id)

                events = [
                    asdict(event)
                    for event in journal.events(
                        self.attempt_id
                    )
                ]
            finally:
                authorizer.close()
                journal.close()

            return {
                "ok": True,
                "result": asdict(result),
                "attempt": (
                    asdict(attempt)
                    if attempt is not None
                    else None
                ),
                "events": events,
                "drift_injected": drift,
                "external_mutation": False,
            }

    def replay_receipt(self):
        """Demonstrate rejection of a consumed receipt on a new attempt."""

        with self._lock:
            if self._token is None:
                raise ValueError(
                    "no authorization receipt has been issued"
                )

            replay_id = self.attempt_id + "-replay"
            journal = self._journal()
            authorizer = self._authorizer()

            try:
                result = authorizer.execute_durable(
                    journal,
                    replay_id,
                    self._token,
                    self.state_snapshot,
                    self.transition,
                    self.code_versions,
                    self.data_versions,
                    self.policy_versions,
                    int(time.time()),
                )

                events = [
                    asdict(event)
                    for event in journal.events(replay_id)
                ]
            finally:
                authorizer.close()
                journal.close()

            return {
                "ok": True,
                "attempt_id": replay_id,
                "result": asdict(result),
                "events": events,
                "single_use_receipt": True,
            }

    def tamper_test(self):
        """Demonstrate exact request-binding protection."""

        with self._lock:
            self.propose()

            altered = deepcopy(
                self.state_snapshot.objects
            )

            altered["service"]["status"] = (
                "UNAUTHORIZED-STATE-CHANGE"
            )

            changed_state = StateSnapshot(
                version=self.state_snapshot.version,
                objects=altered,
            )

            journal = self._journal()
            authorizer = self._authorizer()

            try:
                try:
                    authorizer.begin_attempt(
                        journal,
                        self.attempt_id,
                        changed_state,
                        self.transition,
                        self.code_versions,
                        self.data_versions,
                        self.policy_versions,
                        int(time.time()),
                    )
                except ValueError as exc:
                    return {
                        "ok": True,
                        "blocked": True,
                        "reason": str(exc),
                    }
            finally:
                authorizer.close()
                journal.close()

            return {
                "ok": False,
                "blocked": False,
                "reason": (
                    "tampered request was unexpectedly accepted"
                ),
            }

    def reset(self):
        with self._lock:
            for path in (
                self.approval_database,
                self.journal_database,
            ):
                for candidate in (
                    path,
                    pathlib.Path(str(path) + "-wal"),
                    pathlib.Path(str(path) + "-shm"),
                ):
                    try:
                        candidate.unlink()
                    except FileNotFoundError:
                        pass

            self._token = None
            self._receipt_fingerprint = None
            self._new_attempt()

            return self.state()


class Handler(BaseHTTPRequestHandler):
    controller: DemoController = None

    def _headers(self, status=200, content_type=None):
        self.send_response(status)

        if content_type:
            self.send_header(
                "Content-Type",
                content_type,
            )

        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "X-Content-Type-Options",
            "nosniff",
        )
        self.send_header(
            "X-Frame-Options",
            "DENY",
        )
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; "
            "img-src 'self' data:",
        )

    def _json(self, payload: Any, status=200):
        body = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")

        self._headers(
            status,
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def _index(self):
        body = (
            WEB_ROOT / "index.html"
        ).read_bytes()

        self._headers(
            200,
            "text/html; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/state":
            self._json(self.controller.state())
            return

        if parsed.path == "/api/preview":
            self._json(self.controller.preview())
            return

        if parsed.path in ("/", "/index.html"):
            self._index()
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        actions = {
            "/api/reset": self.controller.reset,
            "/api/propose": self.controller.propose,
            "/api/authorize": self.controller.authorize,
            "/api/execute": (
                lambda: self.controller.execute(False)
            ),
            "/api/execute-drift": (
                lambda: self.controller.execute(True)
            ),
            "/api/replay": (
                self.controller.replay_receipt
            ),
            "/api/tamper": (
                self.controller.tamper_test
            ),
        }

        action = actions.get(parsed.path)

        if action is None:
            self.send_error(404)
            return

        try:
            self._json(action())
        except (
            ValueError,
            PermissionError,
            OSError,
        ) as exc:
            self._json(
                {
                    "ok": False,
                    "error": str(exc),
                },
                400,
            )

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser(
        prog="zyra-cte-demo"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8790,
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
    )

    args = parser.parse_args()

    if args.host not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise SystemExit(
            "Refusing non-loopback bind; "
            "ZYRA-CTE demo is local-only."
        )

    Handler.controller = DemoController()

    server = ThreadingHTTPServer(
        (args.host, args.port),
        Handler,
    )

    url = f"http://127.0.0.1:{args.port}/"

    print("ZYRA-CTE GOVERNMENT / HACKATHON DEMO")
    print("SYNTHETIC-ONLY // HUMAN CONTROL")
    print(url)

    if not args.no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
