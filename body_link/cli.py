from __future__ import annotations

import argparse
import json
import os
import time

from .client import BodyLinkClient
from .server import main as serve


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
