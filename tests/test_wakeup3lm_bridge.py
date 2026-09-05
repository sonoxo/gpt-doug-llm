"""Exercise real bridge HTTP requests against a controlled local Ollama server."""

import http.client
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from wakeup3lm.bridge import MAX_BODY, MAX_INPUT_CHARS, MAX_RESPONSE, BridgeConfig, BridgeServer


@contextmanager
def serving(server):
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def ollama():
    state = {"calls": [], "models": ["qwen2.5-coder:7b", "unapproved:latest"], "error": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, payload):
            raw = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if state["error"]:
                return self.send(500, {"error": "sensitive-upstream-detail"})
            self.send(200, {"models": [{"name": model} for model in state["models"]]})

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["calls"].append({"path": self.path, "payload": payload, "auth": self.headers.get("Authorization")})
            if state.get("wait"):
                state["wait"].wait(timeout=2)
                return
            if state["error"]:
                return self.send(500, {"error": "sensitive-upstream-detail"})
            if state.get("redirect"):
                self.send_response(307)
                self.send_header("Location", "/unexpected-proxy-target")
                return self.end_headers()
            content = "x" * (MAX_RESPONSE + 1) if state.get("oversized") else "print('hello')"
            self.send(200, {"model": payload["model"], "done": not state.get("unfinished"),
                            "message": {"role": "assistant", "content": content}, "eval_count": 5})

    with serving(ThreadingHTTPServer(("127.0.0.1", 0), Handler)) as server:
        state["url"] = f"http://127.0.0.1:{server.server_port}"
        yield state


@pytest.fixture
def bridge(ollama):
    config = BridgeConfig(port=0, ollama_url=ollama["url"], token="test-token-with-enough-entropy",
                          origins=("https://studio.example",), cache_entries=2)
    with serving(BridgeServer(config)) as server:
        yield server


def request(server, method="GET", path="/api/tags", payload=None, headers=None, auth=True, raw=None):
    combined = {"Authorization": "Bearer " + server.config.token} if auth and server.config.token else {}
    if payload is not None:
        raw = json.dumps(payload)
        combined["Content-Type"] = "application/json"
    combined.update(headers or {})
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, body=raw, headers=combined)
        response = connection.getresponse()
        return response.status, dict(response.headers), json.loads(response.read())
    finally:
        connection.close()


def chat(**kwargs):
    return {"model": "qwen2.5-coder:7b", "stream": False,
            "messages": [{"role": "user", "content": "Write hello world"}], **kwargs}


def test_models_health_and_cors_are_truthful(bridge, ollama):
    status, headers, body = request(bridge, headers={"Origin": "https://studio.example"})
    assert status == 200
    assert body == {"models": [{"name": "qwen2.5-coder:7b", "model": "qwen2.5-coder:7b"}], "bridge": "black-house"}
    assert headers["Access-Control-Allow-Origin"] == "https://studio.example"
    assert headers["Cache-Control"] == "no-store"
    status, _, body = request(bridge, path="/health")
    assert status == 200 and body["model_ready"] and not body["inference_verified"]
    ollama["models"] = []
    status, _, body = request(bridge, path="/health")
    assert status == 503 and not body["model_ready"]
    assert not ollama["calls"]  # Health cannot claim a generation was tested.


def test_authentication_and_origin_denial(bridge):
    for method, path in (("GET", "/health"), ("GET", "/api/tags"), ("POST", "/api/chat")):
        status, _, body = request(bridge, method, path, chat() if method == "POST" else None, auth=False)
        assert status == 401
        assert bridge.config.token not in json.dumps(body)
    for origin in ("https://attacker.example", "null", "https://studio.example.attacker.example"):
        status, headers, _ = request(bridge, headers={"Origin": origin})
        assert status == 403 and "Access-Control-Allow-Origin" not in headers
    status, headers, _ = request(bridge, "OPTIONS", "/api/chat", auth=False, headers={
        "Origin": "https://studio.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type, X-Doug-Project",
        "Access-Control-Request-Private-Network": "true",
    })
    assert status == 200
    assert headers["Access-Control-Allow-Private-Network"] == "true"
    assert request(bridge, "OPTIONS", "/api/chat", auth=False, headers={
        "Origin": "https://studio.example", "Access-Control-Request-Headers": "X-Arbitrary-Proxy-URL",
    })[0] == 403


def test_cache_scopes_requests_and_never_forwards_token(bridge, ollama):
    scope = {"X-Doug-Project": "project-one"}
    status, headers, body = request(bridge, "POST", "/api/chat", chat(), scope)
    assert status == 200 and body["message"]["content"] == "print('hello')"
    assert headers["X-Doug-Cache"] == "miss" and not body["cached"]
    assert ollama["calls"][0]["auth"] is None
    assert ollama["calls"][0]["path"] == "/api/chat"
    assert ollama["calls"][0]["payload"]["options"]["num_predict"] == 2048
    assert ollama["calls"][0]["payload"]["options"]["num_ctx"] == 8192
    assert request(bridge, "POST", "/api/chat", chat(), scope)[2]["cached"]
    assert len(ollama["calls"]) == 1
    assert not request(bridge, "POST", "/api/chat", chat(), {"X-Doug-Project": "project-two"})[2]["cached"]
    assert not request(bridge, "POST", "/api/chat", chat(options={"temperature": 0.1}), scope)[2]["cached"]
    assert len(ollama["calls"]) == 3
    # The cache is bounded: two slots evicted project-one's original answer.
    assert len(bridge.cache.items) == 2
    assert not request(bridge, "POST", "/api/chat", chat(), scope)[2]["cached"]
    for _ in range(2):
        assert request(bridge, "POST", "/api/chat", chat())[1]["X-Doug-Cache"] == "disabled"
    assert len(ollama["calls"]) == 6


def test_expired_answers_are_not_reused(bridge, ollama):
    scope = {"X-Doug-Project": "workspace"}
    request(bridge, "POST", "/api/chat", chat(), scope)
    with bridge.cache.lock:
        key = next(iter(bridge.cache.items))
        bridge.cache.items[key] = (0, bridge.cache.items[key][1])
    assert not request(bridge, "POST", "/api/chat", chat(), scope)[2]["cached"]
    assert len(ollama["calls"]) == 2


@pytest.mark.parametrize("payload", [
    chat(model="unapproved:latest"), chat(stream=True), chat(options={"num_predict": -1}),
    chat(options={"num_predict": 2049}), chat(options={"num_ctx": 99999}),
    chat(options={"num_gpu": 999}), chat(options={"temperature": float("nan")}),
    chat(options={"num_predict": True}), chat(ollama_url="http://attacker.example"),
    chat(messages=[{"role": [], "content": "invalid"}]), chat(messages=[]),
    chat(messages=[{"role": "user", "content": "x" * (MAX_INPUT_CHARS + 1)}]),
    chat(messages=[{"role": "user", "content": "hello", "images": ["data"]}]),
])
def test_request_limits_fail_before_inference(bridge, ollama, payload):
    assert request(bridge, "POST", "/api/chat", payload)[0] == 400
    assert not ollama["calls"]


def test_malformed_body_scope_and_unknown_routes(bridge, ollama):
    assert request(bridge, "POST", "/api/chat", raw="{", headers={"Content-Type": "application/json"})[0] == 400
    assert request(bridge, "POST", "/api/chat", chat(), {"X-Doug-Project": "../other"})[0] == 400
    assert request(bridge, "POST", "/api/chat", raw="{}", headers={"Content-Type": "application/json", "Content-Length": str(MAX_BODY + 1)})[0] == 400
    assert request(bridge, "POST", "/api/pull", {"model": "anything"})[0] == 404
    assert not ollama["calls"]


def test_upstream_failures_are_sanitized_and_not_cached(bridge, ollama):
    ollama["error"] = True
    assert request(bridge, path="/health")[0] == 503
    status, _, body = request(bridge, "POST", "/api/chat", chat(), {"X-Doug-Project": "one"})
    assert status == 503 and "sensitive-upstream-detail" not in json.dumps(body)
    assert not bridge.cache.items
    ollama["error"] = False
    for failure in ("unfinished", "redirect", "oversized"):
        ollama[failure] = True
        assert request(bridge, "POST", "/api/chat", chat(), {"X-Doug-Project": "one"})[0] == 503
        ollama[failure] = False
    assert not bridge.cache.items


def test_capacity_is_bounded(bridge, ollama):
    for _ in range(bridge.config.concurrency):
        assert bridge.capacity.acquire(blocking=False)
    try:
        assert request(bridge, "POST", "/api/chat", chat())[0] == 429
        assert not ollama["calls"]
    finally:
        for _ in range(bridge.config.concurrency):
            bridge.capacity.release()


def test_upstream_timeout_returns_retryable_failure(ollama):
    ollama["wait"] = threading.Event()
    try:
        with serving(BridgeServer(BridgeConfig(port=0, ollama_url=ollama["url"], timeout=0.05))) as server:
            status, _, body = request(server, "POST", "/api/chat", chat())
            assert status == 503 and "unavailable" in body["error"]
            assert not server.cache.items
    finally:
        ollama["wait"].set()


def test_loopback_without_token_rejects_rebinding(ollama):
    with serving(BridgeServer(BridgeConfig(port=0, ollama_url=ollama["url"]))) as server:
        assert request(server)[0] == 200
        assert request(server, headers={"Host": "attacker.example"})[0] == 403
        assert request(server, headers={"Origin": "https://attacker.example"})[0] == 403


@pytest.mark.parametrize("options", [
    {"host": "0.0.0.0"}, {"host": "::", "token": "short"},
    {"ollama_url": "http://remote.example:11434"},
    {"ollama_url": "https://secret:password@remote.example"},
    {"ollama_url": "file:///tmp/model"}, {"ollama_url": "https://remote.example/api/chat"},
    {"origins": ("*",)}, {"origins": ("https://studio.example/",)},
    {"origins": ("http://remote.example",)},
])
def test_unsafe_configuration_is_rejected(options):
    with pytest.raises(ValueError):
        BridgeConfig(**options)
