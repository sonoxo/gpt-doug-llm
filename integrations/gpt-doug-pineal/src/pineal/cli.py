"""Local CLI for external AI-memory read/write and advisory GPU telemetry."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from .bridge import read_legacy_memory, read_ontology
from .http_api import PinealHTTPServer
from .kraken import KrakenController, Telemetry
from .store import PinealStore


def state_dir() -> Path:
    return Path(os.environ.get("PINEAL_HOME", str(Path.home() / ".local/share/gpt-doug-pineal"))).expanduser()


def ensure_token(home: Path) -> Path:
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = home / "token"
    if not path.exists():
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write(secrets.token_urlsafe(48) + "\n")
        except FileExistsError:
            pass
    return path


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pineal", description="External GPT-Doug memory I/O and Kraken telemetry")
    p.add_argument("--home", help="local state directory; default ~/.local/share/gpt-doug-pineal")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="initialize SQLite and local API token")
    put = sub.add_parser("put", help="store an ontology triple with provenance")
    put.add_argument("subject")
    put.add_argument("predicate")
    put.add_argument("value")
    put.add_argument("--namespace", default="general")
    put.add_argument("--source", default="user")
    put.add_argument("--confidence", type=float, default=1.0)
    put.add_argument("--ttl-seconds", type=int)
    get = sub.add_parser("get", help="read a memory by ID")
    get.add_argument("id")
    find = sub.add_parser("find", help="search stored ontology triples")
    find.add_argument("query", nargs="?", default="")
    find.add_argument("--namespace")
    find.add_argument("--limit", type=int, default=15)
    revise = sub.add_parser("revise", help="change a triple with revision check")
    revise.add_argument("id")
    revise.add_argument("expected_version", type=int)
    revise.add_argument("subject")
    revise.add_argument("predicate")
    revise.add_argument("value")
    revise.add_argument("--namespace", default="general")
    revise.add_argument("--source", default="user")
    delete = sub.add_parser("delete", help="delete a triple with revision check")
    delete.add_argument("id")
    delete.add_argument("expected_version", type=int)
    context = sub.add_parser("context", help="ontology-first read across GPT-Doug and Pineal memory")
    context.add_argument("query")
    context.add_argument("--gpt-doug-root", default=os.environ.get("PINEAL_GPT_DOUG_ROOT"))
    context.add_argument("--legacy-home", default=os.environ.get("PINEAL_LEGACY_HOME"))
    telemetry = sub.add_parser("telemetry", help="record a simulation-only resource advisory")
    telemetry.add_argument("temperature_c", type=float)
    telemetry.add_argument("power_w", type=float)
    telemetry.add_argument("--water-fraction", type=float, default=1.0)
    sub.add_parser("audit", help="verify audit hash chain")
    sub.add_parser("heartbeat", help="expire memories and append an audit checkpoint")
    serve = sub.add_parser("serve", help="serve authenticated loopback HTTP API")
    serve.add_argument("--port", type=int, default=8765)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.home:
        home = Path(args.home).expanduser()
    else:
        home = state_dir()
    try:
        store = PinealStore(home / "pineal.sqlite3")
        if args.cmd == "init":
            output = {"database": str(store.path), "token_file": str(ensure_token(home)),
                      "network": "loopback only"}
        elif args.cmd == "put":
            output = store.put(subject=args.subject, predicate=args.predicate, value=args.value,
                               namespace=args.namespace, source=args.source,
                               confidence=args.confidence, ttl_seconds=args.ttl_seconds)
        elif args.cmd == "get":
            output = store.get(args.id)
        elif args.cmd == "find":
            output = store.search(query=args.query, namespace=args.namespace, limit=args.limit)
        elif args.cmd == "revise":
            output = store.put(item_id=args.id, expected_version=args.expected_version,
                               subject=args.subject, predicate=args.predicate, value=args.value,
                               namespace=args.namespace, source=args.source)
        elif args.cmd == "delete":
            store.delete(args.id, expected_version=args.expected_version)
            output = {"deleted": args.id}
        elif args.cmd == "context":
            output = {"ontology": read_ontology(args.gpt_doug_root, args.query) if args.gpt_doug_root else [],
                      "legacy_memory": read_legacy_memory(args.legacy_home, args.query) if args.legacy_home else [],
                      "pineal_memory": store.search(query=args.query)}
        elif args.cmd == "telemetry":
            sample = Telemetry(args.temperature_c, args.power_w, args.water_fraction)
            previous = store.latest_telemetry()
            advice = KrakenController().evaluate(sample, previous["mode"] if previous else "nominal")
            record = store.record_telemetry(temperature_c=sample.temperature_c,
                                            power_w=sample.power_w,
                                            water_fraction=sample.water_fraction,
                                            mode=advice.mode, rationale=advice.rationale)
            output = {"advisory": advice.to_dict(), "record": record}
        elif args.cmd == "audit":
            output = store.verify_audit()
        elif args.cmd == "heartbeat":
            output = store.heartbeat()
        elif args.cmd == "serve":
            token = os.environ.get("PINEAL_TOKEN") or ensure_token(home).read_text(encoding="utf-8").strip()
            with PinealHTTPServer(("127.0.0.1", args.port), store, token) as server:
                print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}",
                                  "authentication": "Authorization: Bearer <token>",
                                  "token_file": str(home / "token")}))
                server.serve_forever()
            return 0
        else:
            parser().error("unknown command")
            return 2
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, LookupError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
