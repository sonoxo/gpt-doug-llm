"""GPT-Doug-MAX CoT exercise sender: validated XML and authorized LAN boundary."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import socket
import subprocess
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import tak_cot

ROOT = Path(__file__).resolve().parents[1]


class CotExerciseTests(unittest.TestCase):
    def test_event_has_real_utc_stale_and_escaped_remarks(self):
        now = dt.datetime(2026, 10, 14, 14, 0, 0, tzinfo=dt.timezone.utc)
        packet = tak_cot.build_event(
            "LAB-TEST-1", "medical", 37.54, -77.43,
            callsign="MED & RESCUE", remarks="Exercise <triage> & review",
            ttl=180, now=now,
        )
        event = ET.fromstring(packet)
        self.assertEqual(event.tag, "event")
        self.assertEqual(event.attrib["type"], "a-f-G-I-U-H")
        self.assertEqual(event.attrib["time"], "2026-10-14T14:00:00Z")
        self.assertEqual(event.attrib["start"], "2026-10-14T14:00:00Z")
        self.assertEqual(event.attrib["stale"], "2026-10-14T14:03:00Z")
        self.assertEqual(event.attrib["how"], "m-g")
        self.assertEqual(event.find("point").attrib["ce"], "9999999.0")
        self.assertEqual(event.find("detail/contact").attrib["callsign"], "MED & RESCUE")
        self.assertIn("Exercise <triage> & review", event.findtext("detail/remarks"))
        self.assertNotIn(b"$(date", packet)

    def test_existing_tak_os_lab_decoder_accepts_packet(self):
        path = ROOT / "docs/tak-os/gateway.py"
        spec = importlib.util.spec_from_file_location("tak_cot_local_gateway", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        packet = tak_cot.build_event("DEMO-COT-2", "friendly", 37.54, -77.43)
        event = module.cot_decode(packet)
        self.assertEqual(event["id"], "DEMO-COT-2")
        self.assertTrue(event["synthetic"])
        self.assertEqual(event["cotType"], "a-f-G-U-C")

    def test_refuses_hostile_kinds_real_uids_and_invalid_coordinates(self):
        values = [
            {"uid": "TARGET-1"},
            {"kind": "hostile"},
            {"lat": float("nan")},
            {"lon": float("inf")},
            {"lat": 90.01},
            {"lon": -181},
            {"ttl": 30},
            {"ttl": 3601},
            {"callsign": "\nBAD"},
        ]
        for item in values:
            with self.subTest(item=item), self.assertRaises(ValueError):
                tak_cot.build_event(
                    **{"uid": "LAB-ONE", "kind": "friendly", "lat": 0, "lon": 0, **item}
                )

    def test_lan_only_destinations_and_multicast_explicit(self):
        for host in ("127.0.0.1", "10.0.0.5", "172.16.10.5", "192.168.1.150"):
            self.assertEqual(tak_cot.validate_destination(host), host)
        for bad in (
            "8.8.8.8", "203.0.113.1", "100.64.0.1", "0.0.0.0",
            "255.255.255.255", "239.2.3.1", "example.com", "::1",
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                tak_cot.validate_destination(bad)
        self.assertEqual(
            tak_cot.validate_destination("239.2.3.1", multicast=True), "239.2.3.1"
        )
        with self.assertRaises(ValueError):
            tak_cot.validate_destination("239.2.3.2", multicast=True)

    def test_preview_is_network_free(self):
        output = io.StringIO()
        with mock.patch.object(tak_cot, "send_udp", side_effect=AssertionError("network")):
            with contextlib.redirect_stdout(output):
                self.assertEqual(tak_cot.main([
                    "preview", "--uid", "LAB-PREVIEW", "--lat", "0", "--lon", "0",
                ]), 0)
        event = ET.fromstring(output.getvalue())
        self.assertEqual(event.attrib["uid"], "LAB-PREVIEW")

    def test_send_requires_explicit_operator_authorization(self):
        with mock.patch.object(tak_cot, "send_udp", side_effect=AssertionError("network")):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    tak_cot.main([
                        "send", "--uid", "LAB-NO", "--lat", "0", "--lon", "0",
                        "--host", "127.0.0.1",
                    ])
        self.assertEqual(raised.exception.code, 2)

    def test_explicit_loopback_udp_datagram_and_unconfirmed_receipt(self):
        packet = tak_cot.build_event("LAB-LOOPBACK", "friendly", 0.1, 0.2)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(("127.0.0.1", 0))
            receiver.settimeout(2)
            port = receiver.getsockname()[1]
            sent = tak_cot.send_udp(packet, "127.0.0.1", port)
            message, _address = receiver.recvfrom(16_384)
        self.assertEqual(sent, len(packet))
        self.assertEqual(ET.fromstring(message).attrib["uid"], "LAB-LOOPBACK")

        output = io.StringIO()
        with mock.patch.object(tak_cot, "send_udp", return_value=len(packet)):
            with contextlib.redirect_stdout(output):
                status = tak_cot.main([
                    "send", "--uid", "LAB-LOOPBACK", "--lat", "0.1", "--lon", "0.2",
                    "--host", "127.0.0.1", "--authorize",
                ])
        self.assertEqual(status, 0)
        receipt = json.loads(output.getvalue())
        self.assertEqual(receipt["state"], "UDP_DATAGRAM_SENT_UNCONFIRMED")
        self.assertFalse(receipt["delivery_confirmed"])

    def test_multicast_is_one_hop_and_opt_in(self):
        packet = tak_cot.build_event("LAB-MCAST", "friendly", 0, 0)
        with mock.patch.object(tak_cot.socket, "socket") as factory:
            endpoint = factory.return_value.__enter__.return_value
            endpoint.sendto.return_value = len(packet)
            self.assertEqual(
                tak_cot.send_udp(packet, "239.2.3.1", 6969, multicast=True), len(packet)
            )
            endpoint.setsockopt.assert_any_call(
                socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1
            )
            endpoint.sendto.assert_called_once_with(packet, ("239.2.3.1", 6969))
        with self.assertRaises(ValueError):
            tak_cot.send_udp(packet, "192.168.1.150", 4242, interface="10.0.0.1")

    def test_cli_launcher_is_wired_and_has_valid_bash_syntax(self):
        launcher = ROOT / "scripts/doug-max"
        subprocess.run(["bash", "-n", str(launcher)], check=True, timeout=5)
        completed = subprocess.run([
            "bash", str(launcher), "cot", "preview", "--uid", "LAB-MAX-1",
            "--lat", "0", "--lon", "0",
        ], cwd=ROOT, check=True, capture_output=True, text=True, timeout=10)
        self.assertEqual(ET.fromstring(completed.stdout).attrib["uid"], "LAB-MAX-1")


if __name__ == "__main__":
    unittest.main()
