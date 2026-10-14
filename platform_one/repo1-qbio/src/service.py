"""Repo One / Platform One HTTP wrapper for GPT-Doug QBio analysis.

UNCLASSIFIED - NO CUI.

This service is deliberately read-only. It accepts caller-supplied spike-count
frames and returns descriptive research analytics. It has no hardware control,
no stimulation path, no outbound network access, and no persistent storage.
"""

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from core import MAX_CHANNELS, MAX_FRAMES, SpikeFrame, analyze_sequence

VERSION = "0.1.0"
MAX_BODY_BYTES = 1_048_576
REQUEST_TIMEOUT_SECONDS = 8.0
MAX_CONNECTIONS = 32
ALLOWED_SOURCE_CLASSES = {
    "SIMULATED",
    "MEASURED_READ_ONLY",
    "OPERATOR_DECLARED",
}
SOURCE_RE = re.compile(r"^[A-Z0-9_]{1,64}$")


def _json_bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def build_frames(payload):
    raw_frames = payload.get("frames")
    if not isinstance(raw_frames, list) or not 2 <= len(raw_frames) <= MAX_FRAMES:
        raise ValueError("frames must be an array containing 2..%d entries" % MAX_FRAMES)

    frames = []
    for index, item in enumerate(raw_frames):
        if not isinstance(item, dict):
            raise ValueError("frame %d must be an object" % index)
        if "t_ms" not in item or "counts" not in item:
            raise ValueError("frame %d requires t_ms and counts" % index)
        raw_counts = item["counts"]
        if not isinstance(raw_counts, list) or not 1 <= len(raw_counts) <= MAX_CHANNELS:
            raise ValueError("frame %d counts must contain 1..%d channels" % (index, MAX_CHANNELS))
        if any(type(value) is not int for value in raw_counts):
            raise ValueError("frame %d counts must be JSON integers" % index)
        frames.append(SpikeFrame(t_ms=item["t_ms"], counts=tuple(raw_counts)))
    return frames


def analyze_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")

    window = payload.get("window", 8)
    if type(window) is not int or not 2 <= window <= 128:
        raise ValueError("window must be an integer from 2 through 128")

    source_class = payload.get("source_class", "OPERATOR_DECLARED")
    if not isinstance(source_class, str) or not SOURCE_RE.match(source_class):
        raise ValueError("source_class must be an uppercase provenance label")
    if source_class not in ALLOWED_SOURCE_CLASSES:
        raise ValueError("unsupported source_class")

    frames = build_frames(payload)
    return analyze_sequence(frames, window=window, source_class=source_class)


class BoundedThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = MAX_CONNECTIONS

    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self._slots = threading.BoundedSemaphore(MAX_CONNECTIONS)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "GPTDougQBio/%s" % VERSION
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(REQUEST_TIMEOUT_SECONDS)

    def _send(self, status, payload):
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"status": "ok", "service": "gpt-doug-qbio", "version": VERSION})
            return
        if self.path == "/readyz":
            self._send(200, {"status": "ready", "read_only": True})
            return
        if self.path == "/v1/capabilities":
            self._send(
                200,
                {
                    "service": "gpt-doug-qbio",
                    "version": VERSION,
                    "classification": "UNCLASSIFIED_NO_CUI",
                    "read_only": True,
                    "hardware_control": False,
                    "quantum_hardware": False,
                    "max_frames": MAX_FRAMES,
                    "max_channels": MAX_CHANNELS,
                    "source_classes": sorted(ALLOWED_SOURCE_CLASSES),
                },
            )
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/analyze":
            self._send(404, {"error": "not_found"})
            return

        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("application/json"):
            self._send(415, {"error": "content_type_must_be_application_json"})
            return

        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "0")
        except ValueError:
            self._send(400, {"error": "invalid_content_length"})
            return

        if length <= 0 or length > MAX_BODY_BYTES:
            self._send(413, {"error": "body_size_out_of_bounds"})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = analyze_payload(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._send(400, {"error": "invalid_request", "detail": str(exc)[:240]})
            return
        except Exception:
            self._send(500, {"error": "internal_error"})
            return

        self._send(200, result)

    def log_message(self, fmt, *args):
        # Do not log request bodies or spike data.
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


def main():
    port = int(os.environ.get("PORT", "8080"))
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be 1..65535")
    server = BoundedThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(
        json.dumps(
            {
                "event": "service_started",
                "service": "gpt-doug-qbio",
                "version": VERSION,
                "port": port,
                "classification": "UNCLASSIFIED_NO_CUI",
                "read_only": True,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
