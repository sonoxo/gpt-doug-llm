from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .agents_v031 import AIPDecisionLayer, AppointmentEngine, FriendGate
from .models_v031 import ActionProposal, AgentCandidate, Appointment, Role, TrustState
from .runtime_v031 import VA3LM_LANES, LiveRuntime
from .sources_v031 import CISAKEVSource, NVDSource
from .store_v031 import OntologyStore
from .usb_v031 import USBLayout, install_usb

__all__ = [
    "AIPDecisionLayer",
    "ActionProposal",
    "AgentCandidate",
    "Appointment",
    "AppointmentEngine",
    "CISAKEVSource",
    "FriendGate",
    "LiveRuntime",
    "NVDSource",
    "OntologyStore",
    "Role",
    "TrustState",
    "USBLayout",
    "VA3LM_LANES",
    "install_usb",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kraken-jutsu-live")
    parser.add_argument(
        "--state",
        default=os.getenv("KRAKENXYZ_STATE", ".krakenxyz"),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest-kev")
    sub.add_parser("discover-appoint")
    sub.add_parser("status")
    sub.add_parser("ready")
    nvd = sub.add_parser("nvd")
    nvd.add_argument("--cve", required=True)
    usb = sub.add_parser("init-usb")
    usb.add_argument("--mount", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.cmd == "init-usb":
        layout = install_usb(Path(__file__).resolve().parents[1], args.mount)
        print(
            json.dumps(
                {
                    "mount": str(layout.mount),
                    "runtime": str(layout.runtime),
                    "state": str(layout.state),
                    "va3lm_lanes": list(VA3LM_LANES),
                },
                indent=2,
            )
        )
        return

    runtime = LiveRuntime(args.state)
    if args.cmd == "ingest-kev":
        print(json.dumps({"count": runtime.ingest_kev()}, indent=2))
    elif args.cmd == "discover-appoint":
        print(json.dumps(runtime.discover_appoint_promote(), indent=2))
    elif args.cmd == "nvd":
        print(json.dumps(NVDSource().fetch_cve(args.cve), indent=2))
    elif args.cmd == "ready":
        status = runtime.readiness()
        print(json.dumps(status, indent=2))
        raise SystemExit(0 if status["kraken_ready"] else 2)
    else:
        print(
            json.dumps(
                {
                    "readiness": runtime.readiness(),
                    "agents": runtime.store.list_objects("AgentCandidate"),
                    "sources": runtime.store.list_objects("DataSource"),
                    "actions": runtime.store.list_objects("ActionProposal"),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
