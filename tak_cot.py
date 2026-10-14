#!/usr/bin/env python3
"""Explicitly authorized, exercise-only CoT 2.0 UDP sender for GPT-Doug-MAX.

Independent from the local TAK-OS simulator. No TAK Server/TLS client, sensor
claim, tactical targeting, auto-forwarder or hidden network activity.
"""
from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import json
import math
import re
import socket
import sys
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
MULTICAST_GROUP = "239.2.3.1"
KIND_TYPES = {
    "friendly": "a-f-G-U-C",
    "medical": "a-f-G-I-U-H",
}
UID = re.compile(r"(?:LAB|DEMO)-[A-Za-z0-9_.:@/-]{1,120}\Z")
LAN_RANGES = tuple(
    ipaddress.IPv4Network(cidr)
    for cidr in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
MAX_PACKET = 16_384
UNKNOWN_ACCURACY_METERS = "9999999.0"


def _iso(value: dt.datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_text(text: str, field: str, max_length: int) -> str:
    if not isinstance(text, str) or len(text) > max_length:
        raise ValueError(f"{field} is too long")
    if any(ord(char) < 32 for char in text):
        raise ValueError(f"{field} contains control characters")
    return text


def build_event(
    uid: str,
    kind: str,
    lat: float,
    lon: float,
    *,
    callsign: str = "",
    remarks: str = "",
    ttl: int = 180,
    now: dt.datetime | None = None,
) -> bytes:
    """Build an XML-escaped training packet with real, bounded UTC timestamps."""
    if not isinstance(uid, str) or not UID.fullmatch(uid):
        raise ValueError("UID must begin LAB- or DEMO- and use allowed characters")
    if kind not in KIND_TYPES:
        raise ValueError("only friendly and medical exercise markers are supported")
    latitude, longitude = float(lat), float(lon)
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        raise ValueError("latitude/longitude must be finite WGS84 coordinates")
    if not isinstance(ttl, int) or not 60 <= ttl <= 3600:
        raise ValueError("stale TTL must be 60 to 3600 seconds")
    label = _safe_text(callsign or uid, "callsign", 80)
    annotation = _safe_text(remarks, "remarks", 256)
    current = now if now is not None else dt.datetime.now(UTC)
    stamp = _iso(current)
    stale = _iso(current + dt.timedelta(seconds=ttl))

    event = ET.Element(
        "event",
        {
            "version": "2.0",
            "uid": uid,
            "type": KIND_TYPES[kind],
            "time": stamp,
            "start": stamp,
            "stale": stale,
            "how": "m-g",
        },
    )
    ET.SubElement(
        event,
        "point",
        {
            "lat": f"{latitude:.6f}",
            "lon": f"{longitude:.6f}",
            "hae": UNKNOWN_ACCURACY_METERS,
            "ce": UNKNOWN_ACCURACY_METERS,
            "le": UNKNOWN_ACCURACY_METERS,
        },
    )
    detail = ET.SubElement(event, "detail")
    ET.SubElement(detail, "contact", {"callsign": label})
    ET.SubElement(detail, "remarks").text = (
        "EXERCISE ONLY - operator-entered coordinates, not independently verified."
        + (f" {annotation}" if annotation else "")
    )
    ET.SubElement(detail, "takos", {"synthetic": "true", "source": "operator-training-input"})
    payload = ET.tostring(event, encoding="utf-8", xml_declaration=True)
    if len(payload) > MAX_PACKET:
        raise ValueError("CoT event exceeds packet-size limit")
    return payload


def validate_destination(host: str, *, multicast: bool = False) -> str:
    """Reject DNS, public addresses, broadcast and unapproved multicast groups."""
    try:
        ip = ipaddress.IPv4Address(host)
    except (ipaddress.AddressValueError, TypeError) as exc:
        raise ValueError("destination must be a numeric IPv4 address") from exc
    if multicast:
        if str(ip) != MULTICAST_GROUP:
            raise ValueError("only the configured exercise multicast group is supported")
    elif not any(ip in network for network in LAN_RANGES):
        raise ValueError("destination must be a loopback or RFC1918 private IPv4 address")
    return str(ip)


def send_udp(
    payload: bytes,
    host: str,
    port: int,
    *,
    multicast: bool = False,
    interface: str | None = None,
) -> int:
    """Transmit one UDP datagram. This does not confirm TAK client receipt."""
    target = validate_destination(host, multicast=multicast)
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ValueError("UDP port must be between 1024 and 65535")
    if not payload or len(payload) > MAX_PACKET:
        raise ValueError("packet length is invalid")
    if interface and not multicast:
        raise ValueError("--interface requires --multicast")
    if interface:
        validate_destination(interface)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3)
        if multicast:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            if interface:
                sock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(interface)
                )
        sent = sock.sendto(payload, (target, port))
    if sent != len(payload):
        raise OSError("incomplete UDP send")
    return sent


def parser_for_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "send"):
        command = commands.add_parser(
            name,
            help="print XML without network access" if name == "preview" else "send one training datagram",
        )
        command.add_argument("--uid", required=True, help="LAB- or DEMO- event identifier")
        command.add_argument("--kind", choices=tuple(KIND_TYPES), default="friendly")
        command.add_argument("--lat", type=float, required=True)
        command.add_argument("--lon", type=float, required=True)
        command.add_argument("--callsign", default="")
        command.add_argument("--remarks", default="")
        command.add_argument("--ttl", type=int, default=180, help="stale age in seconds (60-3600)")
        if name == "send":
            command.add_argument("--host", help="explicit private IPv4 unicast destination")
            command.add_argument("--port", type=int, help="default: unicast 4242, multicast 6969")
            command.add_argument("--multicast", action="store_true", help="use 239.2.3.1")
            command.add_argument("--interface", help="local IPv4 interface for multicast")
            command.add_argument(
                "--authorize",
                action="store_true",
                help="confirm destination is yours or explicitly authorized for exercise traffic",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = parser_for_cli()
    args = parser.parse_args(argv)
    if args.command == "send" and not args.authorize:
        parser.error("send requires --authorize (and permission from the network owner)")
    try:
        packet = build_event(
            args.uid,
            args.kind,
            args.lat,
            args.lon,
            callsign=args.callsign,
            remarks=args.remarks,
            ttl=args.ttl,
        )
        if args.command == "preview":
            print(packet.decode("utf-8"))
            return 0
        if not args.multicast and not args.host:
            parser.error("unicast send requires --host")
        host = args.host or MULTICAST_GROUP
        port = args.port if args.port is not None else (6969 if args.multicast else 4242)
        sent = send_udp(
            packet, host, port, multicast=args.multicast, interface=args.interface
        )
        print(json.dumps({
            "state": "UDP_DATAGRAM_SENT_UNCONFIRMED",
            "uid": args.uid,
            "bytes": sent,
            "host": host,
            "port": port,
            "delivery_confirmed": False,
        }, sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        print(f"GPT-DOUG-MAX CoT: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
