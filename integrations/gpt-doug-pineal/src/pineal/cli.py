"""Local CLI for external AI-memory read/write and advisory GPU telemetry."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from .bridge import read_legacy_memory, read_ontology
from .dashboard import run_dashboard
from .blink import run_blink
from .cells import list_cells, search_cells, simulate
from .patents import list_sources, load_records, fetch_ep_metadata, normalize_publication_id
from .patent_connectors import fetch_patent, load_publication_ids, patent_connection_status
from .federation import list_nodes
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
    sub.add_parser("federation", help="list offline provider templates and real access status")
    observe = sub.add_parser("observe", help="append an approved local aggregate or synthetic observation")
    observe.add_argument("node")
    observe.add_argument("metric")
    observe.add_argument("value", type=float)
    observe.add_argument("--unit", default="count")
    observe.add_argument("--source", required=True, help="specific provenance for operator-provided input")
    observe.add_argument("--synthetic", action="store_true")
    dashboard = sub.add_parser("dashboard", help="show ZYRA federation terminal cortex")
    dashboard.add_argument("--demo", action="store_true", help="clearly labeled synthetic signals")
    dashboard.add_argument("--watch", action="store_true", help="redraw until Ctrl+C")
    dashboard.add_argument("--interval", type=float, default=2.0, help="refresh seconds")
    dashboard.add_argument("--frames", type=int, help="limit frames for noninteractive runs")
    dashboard.add_argument("--no-color", action="store_true")
    cells = sub.add_parser("cells", help="curated human cell atlas and educational states")
    cs = cells.add_subparsers(dest="cell_cmd", required=True)
    cs.add_parser("list", help="view known cell types")
    sim = cs.add_parser("simulate", help="symbolic, not biological, state timeline")
    sim.add_argument("cell")
    sim.add_argument("--steps", type=int, default=6)
    patents = sub.add_parser("patents", help="worldwide public patent metadata network")
    ps = patents.add_subparsers(dest="patent_cmd", required=True)
    ps.add_parser("sources", help="view permitted data feeds and limitations")
    ps.add_parser("connect-status", help="show credential readiness (no network requests)")
    imp = ps.add_parser("import", help="import authorized JSONL/JSON/CSV metadata")
    imp.add_argument("file")
    imp.add_argument("--limit", type=int, default=1000)
    search = ps.add_parser("search", help="search offline indexed patents")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--limit", type=int, default=20)
    ps.add_parser("stats", help="local patent index coverage and count")
    fetch = ps.add_parser("fetch", help="opt-in single EPO metadata reference lookup")
    fetch.add_argument("publication_id")
    fetch.add_argument("--online", action="store_true", help="explicitly enable one official request")
    fetch.add_argument("--source", choices=("auto", "epo-linked-open", "epo-ops", "patentsview-us"), default="auto")
    sync = ps.add_parser("sync", help="fetch a bounded list of publication IDs and atomically import")
    sync.add_argument("file", help="UTF-8 text with one exact publication ID per line")
    sync.add_argument("--source", choices=("auto", "epo-linked-open", "epo-ops", "patentsview-us"), default="auto")
    sync.add_argument("--limit", type=int, default=10, help="maximum 20 IDs")
    sync.add_argument("--online", action="store_true")
    sync.add_argument("--dry-run", action="store_true", help="preview without network or database mutation")
    blink = sub.add_parser("blink", help="animate a symbolic cellular heartbeat in Mac Terminal")
    blink.add_argument("--watch", action="store_true")
    blink.add_argument("--frames", type=int)
    blink.add_argument("--interval", type=float, default=0.6)
    blink.add_argument("--no-color", action="store_true")
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
                      "pineal_memory": store.search(query=args.query),
                      "cell_atlas": search_cells(args.query),
                      "patent_publications": store.search_patents(args.query, limit=10),
                      "patent_evidence_notice": "Patent disclosures are not proof of scientific validity."}
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
        elif args.cmd == "federation":
            output = {"nodes": list_nodes(), "connected_count": 0,
                      "observation_mode": "local-only", "no_remote_data": True}
        elif args.cmd == "observe":
            output = store.record_observation(node=args.node, metric=args.metric,
                                              value=args.value, unit=args.unit,
                                              source=args.source, synthetic=args.synthetic)
        elif args.cmd == "dashboard":
            return run_dashboard(store, demo=args.demo, watch=args.watch,
                                 interval=args.interval, frames=args.frames,
                                 color=False if args.no_color else None)
        elif args.cmd == "cells":
            if args.cell_cmd == "list":
                output = {"cells": list_cells(), "claim": "educational metadata, not creation of living cells"}
            else:
                output = simulate(args.cell, steps=args.steps)
        elif args.cmd == "patents":
            if args.patent_cmd == "sources":
                output = {"sources": patent_connection_status(), "connected_count": 0,
                          "globally_complete": False}
            elif args.patent_cmd == "connect-status":
                output = {"sources": patent_connection_status(), "connected_count": 0,
                          "verified_live": False, "no_network_requests": True}
            elif args.patent_cmd == "import":
                records = load_records(args.file, limit=args.limit)
                output = store.import_patents(records)
            elif args.patent_cmd == "search":
                records = store.search_patents(args.query, limit=args.limit)
                output = {"items": records, "count": len(records),
                          "global_corpus_complete": False}
            elif args.patent_cmd == "stats":
                output = store.patent_stats()
            elif args.patent_cmd == "fetch":
                if not args.online:
                    raise ValueError("patents fetch requires explicit --online permission")
                record = fetch_patent(args.publication_id, source=args.source)
                if record.get("publication_id") != normalize_publication_id(args.publication_id):
                    raise ValueError("patent source response ID mismatch")
                output = {"record": record, "import": store.import_patents([record]),
                          "note": "patent metadata is not scientific validation"}
            elif args.patent_cmd == "sync":
                ids = load_publication_ids(args.file, limit=args.limit)
                if args.dry_run:
                    output = {"preview_only": True, "planned_count": len(ids),
                              "ids": ids, "source": args.source, "network_calls": 0}
                else:
                    if not args.online:
                        raise ValueError("patents sync requires explicit --online permission")
                    fetched = [fetch_patent(pub, source=args.source) for pub in ids]
                    if [row.get("publication_id") for row in fetched] != ids:
                        raise ValueError("patent source response IDs do not match requested IDs")
                    output = {"preview_only": False, "fetched": len(fetched),
                              "import": store.import_patents(fetched),
                              "note": "patent publications are disclosures, not scientifically validated research"}
            else:
                raise ValueError("unknown patent command")
        elif args.cmd == "blink":
            return run_blink(store, watch=args.watch, frames=args.frames,
                             interval=args.interval, color=False if args.no_color else None)
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
