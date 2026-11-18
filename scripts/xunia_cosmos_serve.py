#!/usr/bin/env python3
"""XUNIA COSMOS / local-only free static server with bounded port fallback.

Never stop another running process: on the default port, try 8872 through 8899.
An explicit CLI or XUNIA_COSMOS_PORT setting uses exactly the requested port.
"""
from __future__ import annotations

import argparse
import errno
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FIRST_PORT = 8872
LAST_PORT = 8899


def open_server(
    preferred_port: int,
    *,
    auto_fallback: bool = False,
    attempts: int = 28,
    directory: Path = DOCS,
) -> tuple[ThreadingHTTPServer, int]:
    """Bind only to 127.0.0.1; never terminate an existing listener."""
    if not 1024 <= preferred_port <= 65535:
        raise ValueError("Port must be between 1024 and 65535.")
    if attempts < 1:
        raise ValueError("Attempts must be at least one.")
    last = min(65535, preferred_port + (attempts - 1 if auto_fallback else 0))
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    for port in range(preferred_port, last + 1):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), handler)
            server.daemon_threads = True
            return server, port
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE or not auto_fallback:
                raise
    raise OSError(
        errno.EADDRINUSE,
        f"No free local COSMOS port in range {preferred_port}-{last}.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve COSMOS, Planetary Forge and Xenology from localhost."
    )
    parser.add_argument("port", nargs="?", type=int, help="Optional fixed local port.")
    args = parser.parse_args(argv)

    configured = os.environ.get("XUNIA_COSMOS_PORT")
    explicit = args.port is not None or configured not in (None, "")
    try:
        preferred = args.port if args.port is not None else (
            int(configured) if configured else FIRST_PORT
        )
        if not DOCS.is_dir():
            raise ValueError("The repository docs directory does not exist.")
        server, chosen = open_server(
            preferred,
            auto_fallback=not explicit,
            attempts=LAST_PORT - FIRST_PORT + 1 if not explicit else 1,
        )
    except (OSError, ValueError) as exc:
        print(f"XUNIA COSMOS: {exc}", file=sys.stderr)
        print(
            "Choose a different free port: bash scripts/xunia-cosmos serve 8873",
            file=sys.stderr,
        )
        return 1

    if chosen != preferred:
        print(
            f"XUNIA COSMOS: {preferred} is busy; using free localhost port {chosen}.",
            flush=True,
        )
    print(f"XUNIA COSMOS / http://127.0.0.1:{chosen}/cosmos/", flush=True)
    print(f"CL1 XENOLOGY / http://127.0.0.1:{chosen}/cosmos/xenology/", flush=True)
    print(f"PLANETARY FORGE / http://127.0.0.1:{chosen}/cosmos/planets/", flush=True)
    print("Read-only static site; no paid APIs. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nXUNIA COSMOS stopped.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
