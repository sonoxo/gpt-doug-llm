"""Command line for GPT-Doug's local, authorized sensor swarm."""
from __future__ import annotations
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import DEFAULT_DB, Store, demo_specs, load_manifest, snapshot
from .dashboard import HTML
from .ontology import export_graph

def print_json(value):
    print(json.dumps(value, indent=2, sort_keys=True))

def poll_once(specs, *, root, authorized_local, db):
    value = snapshot(specs, root=root, authorized_local=authorized_local)
    store = Store(db)
    try:
        store.write(value)
        return value
    finally:
        store.close()

def serve(specs, *, root, authorized_local, db, port, interval):
    if not 1024 <= port <= 65535:
        raise ValueError("port must be 1024..65535")
    if not 2 <= interval <= 3600:
        raise ValueError("poll interval must be 2..3600 seconds")
    poll_once(specs, root=root, authorized_local=authorized_local, db=db)
    stop = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host", "").split(":", 1)[0].lower() not in {"127.0.0.1", "localhost"}:
                self.send_error(403)
                return
            if self.path == "/":
                body, content_type = HTML.encode("utf-8"), "text/html; charset=utf-8"
            elif self.path == "/api/status":
                store = Store(db)
                try:
                    body = json.dumps(store.status()).encode("utf-8")
                finally:
                    store.close()
                content_type = "application/json; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, fmt, *args):
            return
    def background():
        while not stop.wait(interval):
            try:
                poll_once(specs, root=root, authorized_local=authorized_local, db=db)
            except (OSError, ValueError, PermissionError):
                # Fail closed; the next poll can recover after operator repair.
                continue
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    worker = threading.Thread(target=background, name="swarm-poller", daemon=True)
    worker.start()
    print("Local dashboard: http://127.0.0.1:%s/" % port, flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        worker.join(timeout=2)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("demo", help="Offline BioPineal and synthetic evidence; no writes")
    for action in ("snapshot", "serve"):
        p = commands.add_parser(action, help="Read registered sensors (explicit opt-in)")
        p.add_argument("--config", required=True, help="Approved manifest JSON path")
        p.add_argument("--root", help="Explicitly authorized directory for file sensors")
        p.add_argument("--authorize-local", action="store_true", help="Approve local file/host reads")
        p.add_argument("--db", default=str(DEFAULT_DB), help="Local SQLite path")
        if action == "serve":
            p.add_argument("--port", type=int, default=8765)
            p.add_argument("--interval", type=int, default=5)
    for action in ("status", "ontology"):
        p = commands.add_parser(action, help="Inspect local evidence or export reviewed ontology graph")
        p.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args(argv)
    if args.action == "demo":
        print_json(snapshot(demo_specs()))
        return 0
    if args.action in {"status", "ontology"}:
        store = Store(args.db)
        try:
            print_json(store.status() if args.action == "status" else export_graph(store))
        finally:
            store.close()
        return 0
    specs = load_manifest(args.config)
    if args.action == "snapshot":
        result = poll_once(specs, root=args.root, authorized_local=args.authorize_local, db=args.db)
        print_json({"accepted": result["accepted"], "rejected_sensors": result["rejected_sensors"],
                    "sensors": result["sensors"], "read_only": True})
        return 1 if result["rejected_sensors"] else 0
    serve(specs, root=args.root, authorized_local=args.authorize_local,
          db=args.db, port=args.port, interval=args.interval)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
