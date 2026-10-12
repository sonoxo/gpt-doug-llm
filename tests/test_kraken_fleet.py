"""Deterministic offline tests of human-operated fleet STOP acknowledgements."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import ai_killswitch as ks
import kraken_fleet as fleet


class KrakenFleetTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.t0 = datetime(2026, 10, 12, 15, 0, tzinfo=timezone.utc)
        self.inventory = {
            "schema_version": 1, "fleet_id": "my-owned-fleet",
            "nodes": [{"id": "doug-01", "label": "Primary test agent"},
                      {"id": "zyra-02", "label": "Secondary test agent"}],
        }
        self.campaign = fleet.create_campaign(self.inventory, now=self.t0)
        self.keys = self.root / "keys"
        self.receipts = self.root / "receipts"
        self.keys.mkdir()
        self.receipts.mkdir()
        for node in ("doug-01", "zyra-02"):
            fleet.create_node_key(self.keys / (node + ".key"))
        self.env = mock.patch.dict(os.environ, {
            ks.STATE_DIRECTORY_ENV: str(self.root / "stop"),
            ks.FORCE_STOP_ENV: "0",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def _write_receipt(self, node: str, *, now=None, state=None):
        key = fleet.read_node_key(self.keys / (node + ".key"))
        receipt = fleet.make_receipt(self.inventory, self.campaign, node, key,
                                     now=now or self.t0, stop_state=state)
        (self.receipts / (node + ".json")).write_text(json.dumps(receipt))
        return receipt

    def _stopped(self):
        ks.emergency_stop("offline-test-only")

    def test_campaign_only_creates_id_without_engaging_stop(self):
        self.assertEqual(len(self.campaign["campaign_id"]), 32)
        self.assertFalse(ks.status()["stopped"])
        self.assertFalse((self.root / "stop" / "STOP").exists())

    def test_running_node_is_never_signed_as_stopped(self):
        with self.assertRaisesRegex(fleet.FleetError, "local operator latch"):
            self._write_receipt("doug-01")

    def test_config_error_does_not_count_as_operator_stop(self):
        with self.assertRaises(fleet.FleetError):
            self._write_receipt("doug-01", state={"stopped": True,
                                                  "reason": "invalid_stop_configuration"})

    def test_unknown_node_not_in_inventory_is_rejected(self):
        self._stopped()
        with self.assertRaisesRegex(fleet.FleetError, "not registered"):
            fleet.make_receipt(self.inventory, self.campaign, "intruder", b"X" * 32,
                               now=self.t0)

    def test_valid_locally_stopped_nodes_make_complete_evidence(self):
        self._stopped()
        for node in ("doug-01", "zyra-02"):
            self._write_receipt(node)
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0 + timedelta(seconds=6))
        self.assertTrue(out["coverage_complete"])
        self.assertEqual(out["confirmed_receipts"], 2)
        self.assertEqual(out["expected_nodes"], 2)
        self.assertIn("not proof", out["interpretation"])

    def test_missing_ack_is_fail_closed(self):
        self._stopped()
        self._write_receipt("doug-01")
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0)
        self.assertFalse(out["coverage_complete"])
        self.assertEqual(out["confirmed_receipts"], 1)
        self.assertEqual(out["nodes"][1]["result"], "missing_receipt")

    def test_stale_receipt_is_not_confirmed(self):
        self._stopped()
        self._write_receipt("doug-01")
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0 + timedelta(minutes=6))
        self.assertEqual(out["nodes"][0]["result"], "stale_receipt")
        self.assertFalse(out["coverage_complete"])

    def test_future_receipt_is_not_confirmed(self):
        self._stopped()
        self._write_receipt("doug-01", now=self.t0 + timedelta(seconds=300))
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0)
        self.assertEqual(out["nodes"][0]["result"], "future_receipt")

    def test_tampered_report_signature_is_rejected(self):
        self._stopped()
        signed = self._write_receipt("doug-01")
        signed["stop_reason"] = "host_enforced_stop"
        (self.receipts / "doug-01.json").write_text(json.dumps(signed))
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0)
        self.assertEqual(out["nodes"][0]["result"], "invalid_signature")

    def test_wrong_campaign_is_not_reused(self):
        self._stopped()
        self._write_receipt("doug-01")
        subsequent = fleet.create_campaign(self.inventory, now=self.t0)
        out = fleet.audit_fleet(self.inventory, subsequent, self.receipts, self.keys,
                                now=self.t0)
        self.assertEqual(out["nodes"][0]["result"], "wrong_campaign_or_node")

    def test_key_change_invalidates_report(self):
        self._stopped()
        self._write_receipt("doug-01")
        path = self.keys / "doug-01.key"
        path.unlink()
        fleet.create_node_key(path)
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0)
        self.assertEqual(out["nodes"][0]["result"], "invalid_signature")

    def test_extra_unregistered_receipt_flags_incomplete(self):
        self._stopped()
        self._write_receipt("doug-01")
        self._write_receipt("zyra-02")
        (self.receipts / "unknown-host.json").write_text("{}")
        out = fleet.audit_fleet(self.inventory, self.campaign, self.receipts, self.keys,
                                now=self.t0)
        self.assertFalse(out["coverage_complete"])
        self.assertEqual(out["unregistered_receipts"], ["unknown-host.json"])

    def test_duplicate_and_traversal_node_ids_rejected(self):
        path = self.root / "inventory.json"
        duplicate = copy.deepcopy(self.inventory)
        duplicate["nodes"].append({"id": "doug-01", "label": "duplicate"})
        path.write_text(json.dumps(duplicate))
        with self.assertRaisesRegex(fleet.FleetError, "duplicate"):
            fleet.load_inventory(path)
        duplicate["nodes"][2]["id"] = "../escape"
        path.write_text(json.dumps(duplicate))
        with self.assertRaisesRegex(fleet.FleetError, "invalid node_id"):
            fleet.load_inventory(path)

    @unittest.skipIf(os.name != "posix", "POSIX key permissions required")
    def test_world_readable_and_symlinked_keys_rejected(self):
        path = self.keys / "doug-01.key"
        path.chmod(0o644)
        with self.assertRaisesRegex(fleet.FleetError, "mode 0600"):
            fleet.read_node_key(path)
        path.chmod(0o600)
        fake = self.keys / "fake.key"
        fake.symlink_to(path)
        with self.assertRaises(fleet.FleetError):
            fleet.read_node_key(fake)

    def test_receipt_symlink_not_overwritten(self):
        target = self.root / "target.json"
        target.write_text("protected")
        receipt_path = self.receipts / "doug-01.json"
        receipt_path.symlink_to(target)
        with self.assertRaisesRegex(fleet.FleetError, "unsafe"):
            fleet._write_receipt(receipt_path, {"example": True})
        self.assertEqual(target.read_text(), "protected")

    def test_cli_requires_local_stop_and_returns_nonzero_for_gap(self):
        self.campaign = fleet.create_campaign(self.inventory, now=fleet.utc_now())
        inventory_path = self.root / "inventory.json"
        campaign_path = self.root / "campaign.json"
        inventory_path.write_text(json.dumps(self.inventory))
        campaign_path.write_text(json.dumps(self.campaign))
        output = self.receipts / "doug-01.json"
        args = ["ack", "--inventory", str(inventory_path), "--campaign", str(campaign_path),
                "--node", "doug-01", "--key", str(self.keys / "doug-01.key"),
                "--output", str(output)]
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fleet.main(args), 2)
        self.assertFalse(output.exists())
        self._stopped()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fleet.main(args), 0)
        with contextlib.redirect_stdout(io.StringIO()) as result:
            self.assertEqual(fleet.main(["verify", "--inventory", str(inventory_path),
                                         "--campaign", str(campaign_path),
                                         "--receipts", str(self.receipts),
                                         "--keys", str(self.keys)]), 3)
        self.assertFalse(json.loads(result.getvalue())["coverage_complete"])

    def test_no_receipt_can_claim_global_ai_control(self):
        self._stopped()
        report = self._write_receipt("doug-01")
        self.assertNotIn("external_ai_control", report)
        self.assertNotIn("all_ai_stopped", report)
        self.assertIn("not proof", fleet.audit_fleet(
            self.inventory, self.campaign, self.receipts, self.keys,
            now=self.t0)["interpretation"])


if __name__ == "__main__":
    unittest.main()
