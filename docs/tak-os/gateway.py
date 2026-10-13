#!/usr/bin/env python3
"""GPT-Doug TAK-OS local CoT 2.0 exercise gateway; Python stdlib only.

This is an independent, SYNTHETIC civil-response lab. It is not TAK Server.
No remote TAK connection, privileged traffic, or real-world forwarding is provided.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import mimetypes
import os
import queue
import re
import secrets
import signal
import socket
import sqlite3
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Resolve the adjacent free swarm module both in normal script execution and
# in the existing importlib-based integration test harness.
import importlib.util
_SWARM_FILE = Path(__file__).resolve().parent / "swarm.py"
_SWARM_SPEC = importlib.util.spec_from_file_location("tak_os_swarm", _SWARM_FILE)
_SWARM_MODULE = importlib.util.module_from_spec(_SWARM_SPEC)
_SWARM_SPEC.loader.exec_module(_SWARM_MODULE)
SwarmKernel = _SWARM_MODULE.SwarmKernel

UTC = dt.timezone.utc
APP_ROOT = Path(__file__).resolve().parent
MAX_XML = 16_384
MAX_JSON = 4_096
KEEP_RECORDS = 2_000
COT_UID = re.compile(r"^[A-Za-z0-9_.:@/-]{1,128}$")
LEGACY_COT_PORT = 6969
DEMO = (
    ("LAB-RESCUE-01", "ground", 37.5407, -77.4360, "Richmond demo rescue"),
    ("LAB-MED-02", "ground", 37.5930, -77.4910, "Henrico exercise medic"),
    ("LAB-AIR-03", "air", 37.4513, -77.3194, "Synthetic aerial weather"),
    ("LAB-WX-04", "sensor", 37.8910, -76.3150, "Synthetic weather node"),
    ("LAB-SEA-05", "maritime", 37.0040, -76.3220, "Hampton Roads buoy drill"),
    ("LAB-OPS-06", "ground", 38.3040, -77.4570, "Fredericksburg exercise"),
)


def utcnow() -> str:
    return dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def iso_after(seconds: int) -> str:
    return (dt.datetime.now(UTC) + dt.timedelta(seconds=seconds)).isoformat(timespec="seconds").replace("+00:00", "Z")


def local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def cot_decode(payload: bytes, *, allow_unverified: bool = False) -> dict[str, Any]:
    """Parse a single legacy CoT XML event with strict size/shape restrictions."""
    if not payload or len(payload) > MAX_XML:
        raise ValueError("CoT must be 1 to 16384 bytes")
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", payload, re.IGNORECASE):
        raise ValueError("DTD/entity declarations are prohibited")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError("invalid CoT XML") from exc
    if local_tag(root.tag) != "event":
        raise ValueError("CoT root must be event")
    uid = root.attrib.get("uid", "")
    event_type = root.attrib.get("type", "")
    if not COT_UID.fullmatch(uid) or not event_type or len(event_type) > 96:
        raise ValueError("missing or invalid CoT UID/type")
    if not allow_unverified and not uid.upper().startswith(("DEMO-", "LAB-")):
        raise PermissionError("only synthetic DEMO-/LAB- UIDs accepted by default")
    for name in ("time", "start", "stale"):
        v = root.attrib.get(name)
        if not v:
            raise ValueError(f"CoT {name} is required")
        try:
            when = dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid {name} timestamp") from exc
        if when.tzinfo is None:
            raise ValueError(f"{name} must include timezone")
    point = next((el for el in root if local_tag(el.tag) == "point"), None)
    if point is None:
        raise ValueError("CoT point is required")
    try:
        lat = float(point.attrib["lat"])
        lon = float(point.attrib["lon"])
    except (ValueError, KeyError) as exc:
        raise ValueError("CoT coordinates required") from exc
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("invalid coordinate bounds")
    contact = next((c for el in root.iter() if local_tag(el.tag) == "detail" for c in el.iter() if local_tag(c.tag) == "contact"), None)
    callsign = contact.attrib.get("callsign", "") if contact is not None else ""
    callsign = (callsign[:80] or uid)
    category = next((c.attrib.get("category", "") for el in root.iter() if local_tag(el.tag) == "takos" for c in [el]), "")
    if category not in ("ground", "air", "sensor", "maritime"):
        category = "ground"
    is_synthetic = uid.upper().startswith(("LAB-", "DEMO-"))
    return {
        "id": uid, "type": category, "lat": lat, "lon": lon,
        "label": callsign, "status": "RECEIVED / LAB" if is_synthetic else "UNVERIFIED SOURCE",
        "cotType": event_type, "timestamp": root.attrib["time"],
        "synthetic": is_synthetic,
    }


def cot_encode(entity: dict[str, Any]) -> bytes:
    """Create standards-shaped CoT 2.0 XML for local interop testing."""
    uid = str(entity["id"])
    if not COT_UID.fullmatch(uid):
        raise ValueError("invalid entity UID")
    lat, lon = float(entity["lat"]), float(entity["lon"])
    if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 90 or abs(lon) > 180:
        raise ValueError("coordinates out of bounds")
    now = utcnow()
    event = ET.Element("event", {
        "version": "2.0", "uid": uid, "type": str(entity.get("cotType", "a-f-G-U-C")),
        "how": "m-g", "time": now, "start": now, "stale": iso_after(120),
    })
    ET.SubElement(event, "point", {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "hae": "0", "ce": "25", "le": "25"})
    detail = ET.SubElement(event, "detail")
    ET.SubElement(detail, "contact", {"callsign": str(entity.get("label", uid))[:80]})
    ET.SubElement(detail, "takos", {"category": str(entity.get("type", "ground")), "synthetic": "true"})
    return ET.tostring(event, encoding="utf-8", xml_declaration=True)


class State:
    def __init__(self, db_path: str = ":memory:", allow_unverified: bool = False):
        self.lock = threading.RLock()
        self.cot_encode = cot_encode
        self.token = secrets.token_urlsafe(32)
        self.started = time.monotonic()
        self.stopped = threading.Event()
        self.allow_unverified = allow_unverified
        self.clients: set[queue.Queue[dict[str, Any]]] = set()
        self.entities: dict[str, dict[str, Any]] = {}
        self.tick = 0
        self.ingested = 0
        self.udp_port: int | None = None
        self.tcp_port: int | None = None
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, source TEXT NOT NULL, ts TEXT NOT NULL, uid TEXT, detail TEXT, ack INTEGER NOT NULL DEFAULT 0, synthetic INTEGER NOT NULL DEFAULT 1)")
        self.db.commit()
        for uid, cat, lat, lon, name in DEMO:
            self.entities[uid] = {"id": uid, "type": cat, "lat": lat, "lon": lon, "baseLat": lat, "baseLon": lon, "label": name, "status": "ACTIVE / LAB", "source": "local-simulation", "synthetic": True, "history": [[lat, lon]], "timestamp": utcnow()}
        self.record("system", "gateway", "Local synthetic CoT gateway started", synthetic=True)
        self.swarm = SwarmKernel(self)

    def record(self, kind: str, source: str, detail: str, *, uid: str = "", synthetic: bool = True) -> dict[str, Any]:
        with self.lock:
            now = utcnow()
            cursor = self.db.execute("INSERT INTO events (kind,source,ts,uid,detail,synthetic) VALUES (?,?,?,?,?,?)", (kind, source, now, uid, detail[:300], int(synthetic)))
            self.db.execute("DELETE FROM events WHERE id < (SELECT COALESCE(MAX(id),0)-? FROM events)", (KEEP_RECORDS,))
            self.db.commit()
            row = {"id": cursor.lastrowid, "kind": kind, "source": source, "ts": now, "uid": uid, "detail": detail[:300], "acknowledged": False, "synthetic": synthetic}
            self.publish("record", row)
            return row

    def publish(self, kind: str, item: Any):
        packet = {"kind": kind, "payload": item, "timestamp": utcnow()}
        with self.lock:
            for client in tuple(self.clients):
                try: client.put_nowait(packet)
                except queue.Full:
                    try: client.get_nowait()
                    except queue.Empty: pass
                    try: client.put_nowait(packet)
                    except queue.Full: pass

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {"mode": "synthetic-lab", "tick": self.tick, "units": [dict(u) for u in self.entities.values()], "events": self.list_events(limit=30), "utc": utcnow(), "realTakConnected": False, "source": "loopback-only TAK-OS gateway", "swarmMode": self.swarm.mode}

    def list_events(self, limit: int = 80) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.db.execute("SELECT id,kind,source,ts,uid,detail,ack,synthetic FROM events ORDER BY id DESC LIMIT ?", (min(max(limit, 1), 200),)).fetchall()
            return [{"id": r[0], "kind": r[1], "source": r[2], "ts": r[3], "uid": r[4], "detail": r[5], "acknowledged": bool(r[6]), "synthetic": bool(r[7])} for r in rows]

    def status(self) -> dict[str, Any]:
        with self.lock:
            return {"status": "ok", "mode": "synthetic-lab", "protocol": "CoT 2.0 XML", "transport": "HTTP/SSE, optional UDP 127.0.0.1", "uptimeSeconds": round(time.monotonic()-self.started), "assets": len(self.entities), "tick": self.tick, "acceptedCoT": self.ingested, "udpLoopbackPort": self.udp_port, "tcpLoopbackPort": self.tcp_port, "realTakConnected": False, "externalCoTAllowed": self.allow_unverified, "authorization": "local browser session, no third-party remote access", "apiVersion": "1", "swarmMode":self.swarm.mode, "swarmIntegrity": "VERIFIED" if self.swarm.verify_chain() else "FAILED"}

    def ingest(self, xml: bytes, source: str) -> dict[str, Any]:
        unit = cot_decode(xml, allow_unverified=self.allow_unverified)
        with self.lock:
            before = self.entities.get(unit["id"])
            if before:
                history = (before["history"]+[[unit["lat"], unit["lon"]]])[-30:]
            else:
                history = [[unit["lat"], unit["lon"]]]
            unit.update({
                "source": source,
                "history": history,
                # Preserve the synthetic motion anchor when a local sender uses
                # one of the six built-in LAB UIDs. Never crash the heartbeat.
                "baseLat": before.get("baseLat", unit["lat"]) if before else unit["lat"],
                "baseLon": before.get("baseLon", unit["lon"]) if before else unit["lon"],
            })
            self.entities[unit["id"]] = unit
            self.ingested += 1
            self.record("cot", source, f"CoT position {unit['id']}", uid=unit["id"], synthetic=unit["synthetic"])
            self.publish("cot", unit)
            return dict(unit)

    def advance(self):
        with self.lock:
            self.tick += 1
            for i, (uid, *_unused) in enumerate(DEMO):
                unit = self.entities.get(uid)
                if not unit:
                    continue
                radius = .035 if unit["type"] == "air" else .012 if unit["type"] == "ground" else .004 if unit["type"] == "maritime" else 0
                phase = self.tick *.07 + i
                unit["lat"] = round(unit["baseLat"]+math.sin(phase)*radius, 6)
                unit["lon"] = round(unit["baseLon"]+math.cos(phase)*radius, 6)
                unit["timestamp"] = utcnow()
                unit["history"] = (unit["history"]+[[unit["lat"],unit["lon"]]])[-30:]
            self.publish("telemetry", {"tick": self.tick, "units": [dict(self.entities[u[0]]) for u in DEMO]})
            if self.tick % 10 == 0:
                self.record("heartbeat", "local-simulation", f"Synthetic gateway heartbeat {self.tick}")
            if self.tick % 8 == 0:
                try:
                    self.swarm.pulse()  # read-only challenge/heartbeat, never auto-promote
                except RuntimeError:
                    # A compromised audit chain cannot terminate the synthetic
                    # gateway; all new swarm writes fail closed until reviewed.
                    pass

    def ack(self, event_id: int) -> bool:
        with self.lock:
            row = self.db.execute("UPDATE events SET ack=1 WHERE id=? AND kind='incident'", (event_id,))
            self.db.commit()
            ok = row.rowcount > 0
            if ok: self.publish("ack", {"id": event_id, "acknowledged": True})
            return ok

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        client: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=60)
        with self.lock:
            if len(self.clients) >= 24:
                raise OverflowError("too many SSE clients")
            self.clients.add(client)
        return client

    def unsubscribe(self, client):
        with self.lock: self.clients.discard(client)

    def close(self):
        self.stopped.set()
        self.db.close()


def handler_factory(state: State):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TAKOS-Lab/1.1"
        protocol_version = "HTTP/1.1"
        def log_message(self, format, *args):
            if os.getenv("TAK_OS_DEBUG") == "1":
                super().log_message(format, *args)

        def setup(self):
            super().setup()
            # Bound slow or partially sent browser requests; localhost only.
            self.connection.settimeout(8)

        def respond_headers(self, code: int, content_type: str, length: int | None = None):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://tile.openstreetmap.org data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'; worker-src 'self'; manifest-src 'self'")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            if length is not None: self.send_header("Content-Length", str(length))
            self.end_headers()

        def respond(self, code: int, obj: Any):
            data = json.dumps(obj, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            self.respond_headers(code, "application/json; charset=utf-8", len(data))
            self.wfile.write(data)

        def path_info(self):
            url = urllib.parse.urlsplit(self.path)
            path = url.path
            if path.startswith("/tak-os/"):
                path = path[len("/tak-os"):]
            return path, urllib.parse.parse_qs(url.query)

        def acceptable_host(self):
            host = self.headers.get("Host", "").lower().strip()
            # Fail closed against DNS-rebinding or forged host/port pairs.
            port = self.server.server_port
            return host in {f"localhost:{port}", f"127.0.0.1:{port}"}

        def do_GET(self):
            if not self.acceptable_host():
                return self.respond(403, {"error":"localhost Host header required"})
            path, query = self.path_info()
            if path == "/api/v1/health": return self.respond(200, state.status())
            if path == "/api/v1/session":
                self.respond(200, {**state.status(), "csrfToken": state.token})
                return
            if path == "/api/v1/snapshot": return self.respond(200, state.snapshot())
            if path == "/api/v1/events": return self.respond(200, {"events": state.list_events()})
            if path == "/api/v1/swarm": return self.respond(200, state.swarm.snapshot())
            if path == "/api/v1/swarm/audit": return self.respond(200, state.swarm.audit())
            if path == "/api/v1/cot.xml":
                uid = query.get("uid", ["LAB-RESCUE-01"])[0]
                with state.lock: entity = state.entities.get(uid)
                if not entity or not entity["synthetic"]: return self.respond(404, {"error":"synthetic entity not found"})
                data = cot_encode(entity)
                self.respond_headers(200, "application/xml; charset=utf-8", len(data))
                self.wfile.write(data)
                return
            if path == "/api/v1/stream": return self.stream()
            if path.startswith("/api/"):
                return self.respond(404, {"error": "unknown API endpoint"})
            target = path.lstrip("/") or "index.html"
            if target not in {"index.html", "app.js", "styles.css", "bridge.js", "swarm-ui.js", "icon.svg", "manifest.webmanifest", "sw.js"}:
                return self.respond(404, {"error": "file not available"})
            file = APP_ROOT / target
            if not file.is_file(): return self.respond(404, {"error": "file not found"})
            mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            data = file.read_bytes()
            self.respond_headers(200, mime+("; charset=utf-8" if mime.startswith(("text/", "application/javascript", "application/manifest+json")) else ""), len(data))
            self.wfile.write(data)

        def stream(self):
            try: client = state.subscribe()
            except OverflowError:
                return self.respond(503,{"error": "SSE connection capacity reached"})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                first = json.dumps(state.snapshot(), separators=(",", ":"))
                self.wfile.write(f"event: snapshot\ndata: {first}\n\n".encode())
                self.wfile.flush()
                while not state.stopped.is_set():
                    try: item = client.get(timeout=8)
                    except queue.Empty:
                        self.wfile.write(b": heartbeat\n\n"); self.wfile.flush()
                        continue
                    data = json.dumps(item["payload"], separators=(",", ":"), ensure_ascii=True)
                    name = item["kind"]
                    self.wfile.write(f"event: {name}\ndata: {data}\n\n".encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, TimeoutError): pass
            finally: state.unsubscribe(client)

        def do_POST(self):
            if not self.acceptable_host():
                return self.respond(403, {"error":"localhost Host header required"})
            path, _ = self.path_info()
            origin = self.headers.get("Origin", "")
            host = self.headers.get("Host", "")
            if origin:
                parts = urllib.parse.urlsplit(origin)
                if parts.scheme not in ("http", "https") or parts.netloc.lower() != host.lower():
                    return self.respond(403, {"error":"origin not permitted"})
            if not secrets.compare_digest(self.headers.get("X-TAK-OS-Token", ""), state.token):
                return self.respond(403, {"error": "local session token required"})
            try: length = int(self.headers.get("Content-Length", "0"))
            except ValueError: return self.respond(400, {"error":"invalid content length"})
            if length < 1 or length > MAX_XML:
                return self.respond(413, {"error":"payload length outside allowed range"})
            if path == "/api/v1/cot":
                if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/xml":
                    return self.respond(415, {"error":"application/xml required"})
                xml = self.rfile.read(length)
                try: unit = state.ingest(xml, "authorized-local-http")
                except PermissionError as exc: return self.respond(403, {"error": str(exc)})
                except ValueError as exc: return self.respond(400, {"error": str(exc)})
                return self.respond(201, {"accepted": True, "unit": unit})
            if path in ("/api/v1/incident", "/api/v1/ack", "/api/v1/swarm/control", "/api/v1/swarm/evaluate", "/api/v1/swarm/review"):
                if self.headers.get("Content-Type", "").split(";",1)[0].strip() != "application/json":
                    return self.respond(415, {"error": "application/json required"})
                raw = self.rfile.read(length)
                if len(raw) > MAX_JSON: return self.respond(413,{"error": "JSON too large"})
                try: obj = json.loads(raw)
                except (ValueError, UnicodeDecodeError): return self.respond(400, {"error": "invalid JSON"})
                if not isinstance(obj, dict): return self.respond(400, {"error":"JSON object required"})
                if path.startswith("/api/v1/swarm/"):
                    try:
                        if path.endswith("/control"):
                            action, confirmation = obj.get("action", ""), obj.get("confirmation", "")
                            if not isinstance(action, str) or not isinstance(confirmation, str):
                                raise ValueError("control must be text")
                            return self.respond(200, state.swarm.control(action, confirmation))
                        if path.endswith("/evaluate"):
                            return self.respond(201, state.swarm.evaluate(obj.get("candidate")))
                        proposal_id = obj.get("id")
                        if isinstance(proposal_id, bool) or not isinstance(proposal_id, int) or proposal_id < 1:
                            raise ValueError("positive integer proposal ID required")
                        decision, confirmation = obj.get("decision", ""), obj.get("confirmation", "")
                        if not isinstance(decision, str) or not isinstance(confirmation, str):
                            raise ValueError("review and confirmation must be text")
                        return self.respond(200, state.swarm.review(proposal_id, decision, confirmation))
                    except PermissionError as exc: return self.respond(403, {"error":str(exc)})
                    except LookupError as exc: return self.respond(404, {"error":str(exc)})
                    except OverflowError as exc: return self.respond(429, {"error":str(exc)})
                    except (ValueError, TypeError) as exc: return self.respond(400, {"error":str(exc)})
                    except RuntimeError as exc: return self.respond(409, {"error":str(exc)})
                if path.endswith("incident"):
                    title = str(obj.get("title", "Demo drill"))[:100].strip()
                    if not title: return self.respond(400, {"error":"title required"})
                    event = state.record("incident", "operator-local", title, synthetic=True)
                    return self.respond(201, event)
                try: event_id = int(obj["id"])
                except (KeyError, TypeError, ValueError): return self.respond(400,{"error": "valid id required"})
                if not state.ack(event_id): return self.respond(404, {"error":"incident not found"})
                return self.respond(200, {"acknowledged": True, "id": event_id})
            return self.respond(404, {"error":"unknown endpoint"})
    return Handler


def start_udp_loopback(state: State, port: int):
    """Optional legacy UDP CoT ingest. LOOPBACK ONLY. No multicast, WAN or relaying."""
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", port))
    udp.settimeout(0.5)
    state.udp_port = udp.getsockname()[1]
    def receiver():
        try:
            while not state.stopped.is_set():
                try: payload, addr = udp.recvfrom(MAX_XML + 1)
                except socket.timeout: continue
                if addr[0] != "127.0.0.1": continue
                try: state.ingest(payload, "legacy-udp-loopback")
                except (ValueError, PermissionError): continue
        finally: udp.close()
    thread = threading.Thread(target=receiver, daemon=True, name="legacy-cot-loopback")
    thread.start()
    return thread


def start_tcp_loopback(state: State, port: int):
    """Opt-in unencrypted, *local-only* TCP XML ingest for vintage CoT lab tools.

    Each client may send <= 16KB CoT XML and close its socket. No WAN,
    multicast, TLS impersonation, or TAK Server functionality.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
    sock.listen(4)
    sock.settimeout(0.5)
    state.tcp_port = sock.getsockname()[1]
    def serve_client(conn):
        with conn:
            conn.settimeout(3)
            payload = bytearray()
            while len(payload) < MAX_XML:
                try: chunk = conn.recv(min(4096, MAX_XML-len(payload)))
                except socket.timeout: break
                if not chunk: break
                payload.extend(chunk)
                if b"</event>" in payload or b"</event >" in payload: break
            try: state.ingest(bytes(payload), "legacy-tcp-loopback")
            except (ValueError, PermissionError): pass
    def receiver():
        try:
            while not state.stopped.is_set():
                try: conn,_addr = sock.accept()
                except socket.timeout: continue
                threading.Thread(target=serve_client, args=(conn,),daemon=True).start()
        finally: sock.close()
    thread = threading.Thread(target=receiver, daemon=True, name="legacy-cot-tcp-loopback")
    thread.start()
    return thread


def start_synthetic_clock(state: State, period: float = 1.5):
    def tick():
        while not state.stopped.wait(period): state.advance()
    thread = threading.Thread(target=tick, daemon=True, name="synthetic-tick")
    thread.start()
    return thread


def build_server(host="127.0.0.1", port=8080, db_path=":memory:", udp_port=0, tcp_port=0, allow_unverified=False):
    if host not in ("127.0.0.1", "0.0.0.0"):
        raise ValueError("Only loopback or explicit Docker internal wildcard listener supported")
    if host == "0.0.0.0" and os.getenv("TAK_OS_CONTAINER") != "1":
        raise ValueError("Wildcard binding requires TAK_OS_CONTAINER=1 and loopback-only published Docker port")
    state = State(db_path=db_path, allow_unverified=allow_unverified)
    server = ThreadingHTTPServer((host, port), handler_factory(state))
    server.daemon_threads = True
    server.state = state
    if udp_port: start_udp_loopback(state, udp_port)
    if tcp_port: start_tcp_loopback(state, tcp_port)
    return server, state


def main():
    parser = argparse.ArgumentParser(description="Free independent TAK-OS CoT 2.0 LAB server (loopback)")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.getenv("TAK_OS_PORT", "8080")))
    parser.add_argument("--db", default=os.getenv("TAK_OS_DB", str(Path.home()/".local/state/gpt-doug-tak-os/gateway.sqlite3")))
    parser.add_argument("--udp-port", type=int, default=0, help="opt-in CoT UDP loopback port (e.g. 6969), disabled by default")
    parser.add_argument("--tcp-port", type=int, default=0, help="opt-in CoT TCP loopback port (e.g. 8087), disabled by default")
    parser.add_argument("--allow-unverified-lab-input", action="store_true", help="LAB ONLY: allow external UIDs into local log, never forward externally")
    args = parser.parse_args()
    if args.port < 1024 or args.port > 65535 or args.udp_port < 0 or args.udp_port > 65535 or args.tcp_port < 0 or args.tcp_port > 65535:
        parser.error("ports out of range")
    if args.db != ":memory:": Path(args.db).expanduser().parent.mkdir(parents=True,exist_ok=True)
    server,state = build_server(args.bind, args.port, args.db, args.udp_port, args.tcp_port, args.allow_unverified_lab_input)
    start_synthetic_clock(state)
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(f"GPT-DOUG TAK-OS LAB http://127.0.0.1:{args.port}/ (synthetic local gateway)",flush=True)
    print(f"Legacy UDP: {state.udp_port or 'DISABLED'} | Legacy TCP: {state.tcp_port or 'DISABLED'} | REAL TAK: OFFLINE | remote forwarding: DISABLED",flush=True)
    try: server.serve_forever(poll_interval=0.25)
    finally:
        state.stopped.set(); server.server_close(); state.close()


if __name__ == "__main__":
    main()
