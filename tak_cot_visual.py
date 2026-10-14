"""Open an actual local TAK-OS map focused on a verified exercise CoT event.

All traffic stays on 127.0.0.1. The UI is a synthetic civilian lab, never an
authenticated or operational TAK Server / ATAK / iTAK connection.
"""
from __future__ import annotations

import argparse
import http.client
import importlib.util
import json
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import tak_cot

ROOT = Path(__file__).resolve().parent
GATEWAY_FILE = ROOT / "docs" / "tak-os" / "gateway.py"


def _gateway_module() -> Any:
    spec = importlib.util.spec_from_file_location("gpt_doug_cot_visual_gateway", GATEWAY_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("TAK-OS gateway is unavailable in this checkout")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(port: int) -> dict[str, Any]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET", "/api/v1/snapshot")
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"local dashboard returned HTTP {response.status}")
        return json.loads(response.read(64_000).decode("utf-8"))
    finally:
        connection.close()


def stop_dashboard(handle: dict[str, Any]) -> None:
    handle["state"].stopped.set()
    handle["server"].shutdown()
    handle["server"].server_close()
    handle["thread"].join(timeout=3)
    handle["state"].close()


def start_dashboard(
    *,
    uid: str = "LAB-VISIBLE-001",
    kind: str = "medical",
    lat: float = 34.6100,
    lon: float = -86.5900,
    callsign: str = "TRAINING-HLZ",
) -> dict[str, Any]:
    """Launch an isolated loopback gateway, send one CoT, confirm API visibility."""
    payload = tak_cot.build_event(
        uid,
        kind,
        lat,
        lon,
        callsign=callsign,
        remarks="GPT-Doug-MAX visible CoT interoperability test",
    )
    gateway = _gateway_module()
    server, state = gateway.build_server(
        host="127.0.0.1", port=0, db_path=":memory:", udp_port=0
    )
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.1},
        daemon=True,
        name="gpt-doug-cot-visual-web",
    )
    thread.start()
    handle = {"server": server, "state": state, "thread": thread}
    try:
        gateway.start_udp_loopback(state, 0)
        udp_port = state.udp_port
        tak_cot.send_udp(payload, "127.0.0.1", udp_port)
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            snapshot = _snapshot(server.server_port)
            matched = next(
                (
                    item
                    for item in snapshot.get("units", [])
                    if item.get("id") == uid
                    and item.get("source") == "legacy-udp-loopback"
                    and item.get("synthetic") is True
                ),
                None,
            )
            if matched:
                url = (
                    f"http://127.0.0.1:{server.server_port}/?"
                    + urllib.parse.urlencode({"cot": uid})
                )
                return {
                    **handle,
                    "url": url,
                    "uid": uid,
                    "unit": matched,
                    "http_port": server.server_port,
                    "udp_port": udp_port,
                }
            time.sleep(0.05)
        raise RuntimeError("CoT not ingested by local UDP gateway before timeout")
    except BaseException:
        stop_dashboard(handle)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uid", default="LAB-VISIBLE-001")
    parser.add_argument("--kind", choices=tuple(tak_cot.KIND_TYPES), default="medical")
    parser.add_argument("--lat", type=float, default=34.6100)
    parser.add_argument("--lon", type=float, default=-86.5900)
    parser.add_argument("--callsign", default="TRAINING-HLZ")
    parser.add_argument("--no-open", action="store_true", help="print URL without opening browser")
    args = parser.parse_args(argv)

    try:
        handle = start_dashboard(
            uid=args.uid,
            kind=args.kind,
            lat=args.lat,
            lon=args.lon,
            callsign=args.callsign,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(2, f"GPT-DOUG-MAX CoT VISUAL: {exc}\n")

    try:
        print("GPT-DOUG-MAX CoT VISUAL: READY (LOCAL EXERCISE ONLY)", flush=True)
        print(f"OPEN THIS MAP: {handle['url']}", flush=True)
        print(f"CoT {args.uid} RECEIVED on UDP 127.0.0.1:{handle['udp_port']}", flush=True)
        print("Verified: local UDP -> CoT gateway -> HTTP snapshot -> browser map.", flush=True)
        print("No ATAK/iTAK client or external TAK Server is connected.", flush=True)
        print("Keep this Terminal open. Press Ctrl+C to stop.", flush=True)
        if not args.no_open:
            opened = webbrowser.open(handle["url"], new=2)
            if not opened:
                print("Browser did not open automatically. Open the URL printed above.", flush=True)
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\nStopping local TAK-OS dashboard.", flush=True)
        return 0
    finally:
        stop_dashboard(handle)


if __name__ == "__main__":
    raise SystemExit(main())
