"""CLI for launching, diagnosing and manually guarding integrated AI requests."""
from __future__ import annotations

import argparse
import atexit
import importlib.resources
import shutil
import tempfile
import json
import os
import secrets
import stat
import sys
from pathlib import Path

from .core import Watchtower
from .server import WatchtowerHTTPServer


def credentials(path: Path) -> dict:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise PermissionError("credential path must not be a symlink")
    if path.parent.stat().st_mode & 0o077:
        raise PermissionError("state directory must be private (0700)")
    if path.exists():
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_mode & 0o077:
            raise PermissionError("credential file must be a private regular file (0600)")
        data = json.loads(path.read_text())
    else:
        data = {"operator_token": secrets.token_urlsafe(36),
                "audit_key_hex": secrets.token_hex(32)}
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream)
    return data


def default_ui_root() -> str:
    """Serve bundled assets from either a source checkout, installed wheel, or zipapp."""
    here = Path(__file__).resolve().parent / "static"
    if here.is_dir():
        return str(here)
    temporary = Path(tempfile.mkdtemp(prefix="xunia-watchtower-static-"))
    temporary.chmod(0o700)
    atexit.register(lambda: shutil.rmtree(temporary, ignore_errors=True))
    assets = importlib.resources.files("universal_watchdog").joinpath("static")
    for asset in assets.iterdir():
        if asset.name not in ("index.html", "app.js", "style.css", "demo.json", "ontology.json"):
            continue
        (temporary / asset.name).write_bytes(asset.read_bytes())
    return str(temporary)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="GPT-Doug model-neutral RSI Watchtower")
    p.add_argument("command", choices=["serve", "doctor", "evaluate", "stop", "rearm"])
    p.add_argument("--state-dir", default=str(Path.home() / ".gpt-doug" / "watchtower"))
    p.add_argument("--port", type=int, default=8877)
    p.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1"])
    p.add_argument("--ui-root", default=None)
    args = p.parse_args(argv)
    root = Path(args.state_dir).expanduser().absolute()
    creds = credentials(root / "credentials.json")
    operator_token = os.environ.get("WATCHTOWER_OPERATOR_TOKEN", creds["operator_token"])
    audit_key = bytes.fromhex(os.environ.get("WATCHTOWER_AUDIT_KEY_HEX", creds["audit_key_hex"]))
    engine = Watchtower(root / "watchtower.sqlite3", audit_key)
    try:
        if args.command == "doctor":
            print(json.dumps(engine.overview(), indent=2))
            return 0
        if args.command == "evaluate":
            try:
                result = engine.evaluate(json.load(sys.stdin))
                print(json.dumps(result, indent=2))
                return 0 if result["enforce"] else 3
            except Exception as exc:
                print(json.dumps({"verdict": "deny", "error": type(exc).__name__}), file=sys.stderr)
                return 3
        if args.command == "stop":
            print(json.dumps(engine.stop("operator_cli_stop")))
            return 0
        if args.command == "rearm":
            if not sys.stdin.isatty():
                raise PermissionError("local rearm requires an interactive terminal")
            phrase = input("Type REARM WATCHTOWER to rearm: ")
            print(json.dumps(engine.rearm(phrase)))
            return 0
        if args.command == "serve":
            server = WatchtowerHTTPServer((args.host, args.port), engine, operator_token, args.ui_root or default_ui_root())
            print(f"WATCHTOWER READY: http://{args.host}:{server.server_address[1]}/", flush=True)
            print(f"Operator token (localhost only): {operator_token}", flush=True)
            print("Operator credential stored in private state credentials.json; per-model ingest tokens are issued upon operator enrollment.", flush=True)
            try:
                server.serve_forever(poll_interval=0.1)
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
    finally:
        engine.store.close()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
