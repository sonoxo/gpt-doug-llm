"""Exercise the streaming GPT-Doug bridge against a controlled Ollama server."""

from __future__ import annotations

import http.client
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from wakeup3lm.stream_bridge import BridgeConfig, StreamingBridgeServer


@contextmanager
def serving(server):
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.02},
        daemon=True,
    )
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def fake_ollama(*, invalid=False, unfinished=False):
    state = {"payloads": []}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def do_GET(self):
            raw = json.dumps({"models": [{"name": "qwen2.5-coder:7b"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["payloads"].append(payload)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            if invalid:
                self.wfile.write(b"not-json\n")
                self.wfile.flush()
                return
            chunks = [
                {"model": payload["model"], "message": {"role": "assistant", "content": '{"message":"ok",'}, "done": False},
                {"model": payload["model"], "message": {"role": "assistant", "content": '"operations":[]}'}, "done": not unfinished, "eval_count": 7},
            ]
            for chunk in chunks:
                self.wfile.write(json.dumps(chunk).encode() + b"\n")
                self.wfile.flush()

    with serving(ThreadingHTTPServer(("127.0.0.1", 0), Handler)) as server:
        state["url"] = f"http://127.0.0.1:{server.server_port}"
        yield state


def request(server, method, path, *, payload=None, headers=None):
    combined = dict(headers or {})
    raw = None
    if payload is not None:
        raw = json.dumps(payload)
        combined["Content-Type"] = "application/json"
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, body=raw, headers=combined)
        response = connection.getresponse()
        return response.status, dict(response.headers), response.read()
    finally:
        connection.close()


def chat(stream=True):
    return {
        "model": "qwen2.5-coder:7b",
        "stream": stream,
        "format": "json",
        "messages": [{"role": "user", "content": "Return JSON"}],
        "options": {"temperature": 0, "num_predict": 64, "num_ctx": 1024},
    }


def test_streaming_preflight_and_incremental_response():
    with fake_ollama() as ollama:
        config = BridgeConfig(
            port=0,
            ollama_url=ollama["url"],
            origins=("http://localhost:8787",),
        )
        with serving(StreamingBridgeServer(config)) as bridge:
            status, headers, raw = request(
                bridge,
                "OPTIONS",
                "/api/chat/stream",
                headers={
                    "Origin": "http://localhost:8787",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type, X-Doug-Project",
                    "Access-Control-Request-Private-Network": "true",
                },
            )
            assert status == 200
            assert json.loads(raw) == {"ok": True, "stream": "ndjson"}
            assert headers["Access-Control-Allow-Origin"] == "http://localhost:8787"
            assert headers["Access-Control-Allow-Private-Network"] == "true"

            status, headers, raw = request(
                bridge,
                "POST",
                "/api/chat/stream",
                payload=chat(),
                headers={"Origin": "http://localhost:8787", "X-Doug-Project": "demo"},
            )
            assert status == 200
            assert headers["X-Doug-Stream"] == "ndjson"
            chunks = [json.loads(line) for line in raw.splitlines() if line]
            assert len(chunks) == 2
            assert chunks[0]["message"]["content"] == '{"message":"ok",'
            assert chunks[-1]["done"] is True
            assert all(chunk["bridge"] == "black-house" for chunk in chunks)
            assert ollama["payloads"][0]["stream"] is True


def test_stream_route_requires_stream_true():
    with fake_ollama() as ollama:
        with serving(StreamingBridgeServer(BridgeConfig(port=0, ollama_url=ollama["url"]))) as bridge:
            status, _, raw = request(bridge, "POST", "/api/chat/stream", payload=chat(stream=False))
            assert status == 400
            assert "stream:true" in json.loads(raw)["error"]
            assert not ollama["payloads"]


def test_invalid_or_unfinished_upstream_stream_is_sanitized():
    for options in ({"invalid": True}, {"unfinished": True}):
        with fake_ollama(**options) as ollama:
            with serving(StreamingBridgeServer(BridgeConfig(port=0, ollama_url=ollama["url"]))) as bridge:
                status, _, raw = request(bridge, "POST", "/api/chat/stream", payload=chat())
                assert status == 200
                chunks = [json.loads(line) for line in raw.splitlines() if line]
                assert chunks[-1]["done"] is True
                assert "invalid streaming response" in chunks[-1]["error"]
