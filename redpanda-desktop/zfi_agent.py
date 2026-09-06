#!/usr/bin/env python3
"""ZYRA File Intelligence (ZFI) local USB-backed intake service.

Uses only stdlib APIs available on current Python, including Python 3.13+.
Officially classified material is rejected from this ordinary workstation/Drive pipeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import time
from email.parser import BytesParser
from email.policy import default as email_policy
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

DEFAULT_PORT = int(os.environ.get("ZFI_PORT", "8766"))
NODE_MARKER = ".gpt-redpanda-node"
ROOT = Path(__file__).resolve().parent
USB_ROOT = Path(os.environ.get("REDPANDA_USB_ROOT", ROOT.parent)).resolve()
STATE_ROOT = USB_ROOT / ".redpanda"
TOKEN_FILE = STATE_ROOT / "portal-token"
ZFI_ROOT = STATE_ROOT / "zfi"
INBOX = ZFI_ROOT / "00_INBOX"
PUBLIC = ZFI_ROOT / "01_PUBLIC_RELEASE"
INTERNAL = ZFI_ROOT / "02_UNCLASSIFIED_INTERNAL"
REVIEW = ZFI_ROOT / "03_RESTRICTED_REVIEW"
QUARANTINE = ZFI_ROOT / "99_QUARANTINE"
AUDIT = ZFI_ROOT / "audit.jsonl"
MAX_FILE_BYTES = int(os.environ.get("ZFI_MAX_FILE_BYTES", str(250 * 1024 * 1024)))

for directory in (ZFI_ROOT, INBOX, PUBLIC, INTERNAL, REVIEW, QUARANTINE):
    directory.mkdir(parents=True, exist_ok=True)


def token() -> str:
    value = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError("GPT-REDPANDA portal token is missing")
    return value


PORTAL_TOKEN = token()


def safe_name(name: str) -> str:
    base = Path(name or "upload.bin").name
    cleaned = "".join(ch if ch.isalnum() or ch in ".-_ ()[]" else "_" for ch in base).strip(" .")
    return cleaned[:180] or "upload.bin"


def unique_path(directory: Path, name: str) -> Path:
    target = directory / name
    if not target.exists():
        return target
    stamp = time.strftime("%Y%m%d-%H%M%S")
    counter = 1
    while True:
        candidate = directory / f"{target.stem}-{stamp}-{counter}{target.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_audit(event: dict[str, Any]) -> None:
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def destination_for(handling: str) -> Path | None:
    return {"PUBLIC_RELEASE": PUBLIC, "UNCLASSIFIED_INTERNAL": INTERNAL, "RESTRICTED_REVIEW": REVIEW}.get(handling)


def ingest(temp_path: Path, original_name: str, system: str, handling: str, source: str) -> dict[str, Any]:
    system = (system or "ZYRA").upper().strip()[:64]
    handling = handling.upper().strip()
    if handling == "CLASSIFIED_MARKED":
        temp_path.unlink(missing_ok=True)
        event = {"accepted": False, "reason": "CLASSIFIED_MARKED material is rejected from the ordinary ZFI/Drive pipeline", "system": system, "handling": handling, "received_at": int(time.time())}
        append_audit(event)
        return event
    destination = destination_for(handling)
    if destination is None:
        destination, handling = REVIEW, "RESTRICTED_REVIEW"
    final = unique_path(destination / system, safe_name(original_name))
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(temp_path), str(final))
    manifest = {
        "schema": "zfi.manifest.v1", "system": system, "source": source, "handling": handling,
        "public_release": handling == "PUBLIC_RELEASE", "received_at": int(time.time()),
        "sha256": sha256(final), "original_filename": safe_name(original_name), "stored_path": str(final),
        "bytes": final.stat().st_size, "drive_sync": "NOT_CONFIGURED",
        "classification_note": "Handling is a release-control decision. Official classification requires authoritative marking."
    }
    manifest_path = final.with_name(final.name + ".meta.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_audit({"accepted": True, **manifest})
    return {"accepted": True, "manifest": manifest, "manifest_path": str(manifest_path)}


def parse_multipart(headers: Any, body: bytes) -> tuple[bytes, str, str, str]:
    content_type = headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type.lower():
        raise ValueError("multipart/form-data required")
    raw = (f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n").encode() + body
    message = BytesParser(policy=email_policy).parsebytes(raw)
    file_bytes = None
    filename = "upload.bin"
    fields: dict[str, str] = {}
    for part in message.iter_parts():
        disposition = part.get("Content-Disposition", "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        payload = part.get_payload(decode=True) or b""
        if name == "file":
            file_bytes = payload
            filename = part.get_filename() or "upload.bin"
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    if file_bytes is None:
        raise ValueError("file is required")
    return file_bytes, filename, fields.get("system", "ZYRA"), fields.get("handling", "RESTRICTED_REVIEW")


HTML = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ZYRA File Intelligence</title><style>:root{color-scheme:dark;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#08090c;color:#f5f5f7}body{margin:0;padding:24px;min-height:100vh;background:radial-gradient(circle at 15% 0%,#16344d 0,#08090c 45%)}main{max-width:900px;margin:auto}.card{background:#11141a;border:1px solid #29313e;border-radius:18px;padding:18px;margin:14px 0;box-shadow:0 18px 45px #0008}h1{font-size:clamp(30px,6vw,58px);margin:0}.sub{opacity:.7;margin:8px 0 18px}.drop{border:2px dashed #40536b;border-radius:16px;padding:28px;text-align:center}input,select,button{font:inherit;color:#fff;background:#0b0e13;border:1px solid #364252;border-radius:10px;padding:11px;margin:5px}button{cursor:pointer;background:#1d3044}.ok{color:#7dff9b}.bad{color:#ff7d8b}pre{white-space:pre-wrap;word-break:break-word}</style></head><body><main><h1>📁 ZYRA FILE INTELLIGENCE</h1><div class='sub'>GPT‑REDPANDA • USB-backed intake • release boundary • SHA-256 manifests</div><div class='card'><strong>Boundary</strong><p>PUBLIC_RELEASE → publication candidate. UNCLASSIFIED_INTERNAL → private. RESTRICTED_REVIEW → never auto-publish. CLASSIFIED_MARKED → rejected from this workstation/Drive pipeline.</p></div><div class='card drop'><form id='form'><input type='file' name='file' required><br><select name='system'><option>ZYRA</option><option>BLACK_HOUSE</option><option>RVIA</option><option>VA3LM</option><option>WAKEUP3LM</option><option>XUNIA</option><option>NXYZ</option><option>AIP_PALANTIR</option></select><select name='handling'><option>RESTRICTED_REVIEW</option><option>UNCLASSIFIED_INTERNAL</option><option>PUBLIC_RELEASE</option><option>CLASSIFIED_MARKED</option></select><br><button type='submit'>📥 Intake file</button></form></div><div class='card'><strong>Result</strong><pre id='out'>Ready.</pre></div></main><script>const token=new URLSearchParams(location.search).get('token')||'';document.getElementById('form').onsubmit=async e=>{e.preventDefault();const out=document.getElementById('out');out.textContent='Hashing and routing locally…';const data=new FormData(e.target);const r=await fetch('/api/intake?token='+encodeURIComponent(token),{method:'POST',body:data});const j=await r.json();out.textContent=JSON.stringify(j,null,2);out.className=j.accepted?'ok':'bad';};</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "ZFI/1.1"
    def authorized(self) -> bool:
        supplied = (parse_qs(urlparse(self.path).query).get("token") or [""])[0]
        return secrets.compare_digest(supplied, PORTAL_TOKEN)
    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self) -> None:
        if not self.authorized(): return self.send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
        if urlparse(self.path).path != "/": return self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        body = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self) -> None:
        if not self.authorized(): return self.send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
        if urlparse(self.path).path != "/api/intake": return self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length <= 0 or length > MAX_FILE_BYTES + 1024 * 1024:
                return self.send_json({"error": "invalid or oversized upload"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            data, filename, system, handling = parse_multipart(self.headers, self.rfile.read(length))
            if len(data) > MAX_FILE_BYTES: return self.send_json({"error": "file exceeds ZFI_MAX_FILE_BYTES"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            temp = unique_path(INBOX, safe_name(filename) + ".uploading")
            temp.write_bytes(data)
            result = ingest(temp, filename, system, handling, "redpanda-local-upload")
            self.send_json(result, 200 if result.get("accepted") else HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> int:
    parser = argparse.ArgumentParser(prog="zfi-agent", description="ZYRA File Intelligence local intake")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT); args = parser.parse_args()
    if not (USB_ROOT / NODE_MARKER).exists(): raise SystemExit("GPT-REDPANDA USB node is not mounted")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"📁 ZFI ONLINE http://127.0.0.1:{args.port}/?token={PORTAL_TOKEN}", flush=True)
    try: server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__": raise SystemExit(main())
