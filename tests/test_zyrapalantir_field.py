from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "zyrapalantir_field.py"
SPEC = importlib.util.spec_from_file_location("zyrapalantir_field", MODULE_PATH)
assert SPEC and SPEC.loader
field = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(field)


class ZyrapalantirFieldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        field.STATE_DIR = root
        field.DEFENSE_STATE = root / "defense-profile.json"
        field.LIVE_STATE = root / "zyrapalantir-live-state.json"
        field.LIVE_PID = root / "zyrapalantir-live.pid"
        field.FIELD_STATE = root / "zyrapalantir-field-state.json"
        field.FIELD_AUDIT = root / "zyrapalantir-field-audit.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ready_snapshot_keeps_external_controls_disabled(self) -> None:
        field.DEFENSE_STATE.write_text(json.dumps({"active": True}), encoding="utf-8")
        field.LIVE_STATE.write_text(
            json.dumps(
                {
                    "readiness": "READY",
                    "maven_ok": True,
                    "cpr_ok": True,
                    "highest_severity": "MEDIUM",
                    "needs_alert": False,
                    "severity_counts": {"LOW": 1, "MEDIUM": 1, "HIGH": 0, "CRITICAL": 0},
                    "findings": [],
                }
            ),
            encoding="utf-8",
        )
        field.LIVE_PID.write_text(str(os.getpid()), encoding="utf-8")

        snap = field.snapshot()

        self.assertTrue(snap["field_ready"])
        self.assertFalse(snap["automatic_external_action"])
        self.assertFalse(snap["weapons_control"])
        self.assertFalse(snap["targeting_control"])

    def test_imported_data_requires_explicit_authorization_ack(self) -> None:
        data = Path(self.tmp.name) / "field.json"
        data.write_text(json.dumps({"assets": []}), encoding="utf-8")
        previous = os.environ.pop("ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK", None)
        try:
            with self.assertRaises(SystemExit):
                field.load_authorized_data(str(data))
        finally:
            if previous is not None:
                os.environ["ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK"] = previous


if __name__ == "__main__":
    unittest.main()
