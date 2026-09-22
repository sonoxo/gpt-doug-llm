from __future__ import annotations

import argparse
import json
import os
import time

from .client import BodyLinkClient
from .server import main as serve
from .state import ALLOWED_BODY_STATES


def _client() -> BodyLinkClient:
    url = os.getenv("GPT_DOUG_BODY_URL", "")
    key = os.getenv("GPT_DOUG_BODY_LINK_KEY", "")
    return BodyLinkClient(url, key)


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug-body")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("link")
    sub.add_parser("ping")
    sub.add_parser("serve")

    state = sub.add_parser("state", help="Push one signed body state.")
    state.add_argument("name", choices=ALLOWED_BODY_STATES)
    state.add_argument("--detail", default="")

    demo = sub.add_parser("demo", help="Cycle all canonical body states.")
    demo.add_argument("--interval", type=float, default=2.0)
    watch = sub.add_parser("watch")
    watch.add_argument("--interval", type=int, default=30)

    args = parser.parse_args()
    if args.command == "serve":
        return serve()

    if args.command == "status" and not os.getenv("GPT_DOUG_BODY_URL", "").strip() and not os.getenv("GPT_DOUG_BODY_LINK_KEY", ""):
        _print({
            "configured": False,
            "workspace_url": BodyLinkClient.WORKSPACE_URL,
            "required_env": ["GPT_DOUG_BODY_URL", "GPT_DOUG_BODY_LINK_KEY"],
        })
        return 0

    client = _client()
    if args.command == "status":
        _print(client.status())
        return 0
    if args.command == "link":
        _print(client.link())
        return 0
    if args.command == "ping":
        _print(client.ping())
        return 0
    if args.command == "state":
        _print(client.push_runtime_state(args.name, args.detail))
        return 0
    if args.command == "demo":
        interval = max(0.25, min(float(args.interval), 30.0))
        for name in ALLOWED_BODY_STATES:
            _print(client.push_runtime_state(name, f"body demo: {name.lower()}"))
            time.sleep(interval)
        _print(client.push_runtime_state("IDLE", "body demo complete"))
        return 0
    if args.command == "watch":
        interval = max(5, min(args.interval, 3600))
        while True:
            try:
                _print(client.ping())
            except Exception as exc:
                _print({"status": "DEGRADED", "error": str(exc)})
            time.sleep(interval)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
