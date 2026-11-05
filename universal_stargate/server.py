"""Universal Stargate: operator-controlled, local-only Ollama gateway.

No arbitrary URLs, agent execution, remote model endpoints or repo mutation.
The gateway is NOT an actual superintelligence system. All nodes besides
BrainRouter and local Ollama are ontology references, not live integrations.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from ai_killswitch import require_ai_allowed, status as stop_status, AIKillSwitchEngaged

STATIC = Path(__file__).with_name("static")
OLLAMA_API = "http://127.0.0.1:11434"
DEFAULT_MODEL = os.getenv("STARGATE_MODEL", "qwen2.5:3b")
MODEL_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,90}(?::[a-zA-Z0-9][a-zA-Z0-9._-]{0,40})?$")
MAX_INPUT = 32 * 1024
MAX_MESSAGES = 12
MAX_MESSAGE = 3000
_MAX_PARALLEL_INFERENCE = threading.BoundedSemaphore(2)

POLICY = {
    "schema": "stargate.si.policy.v1", "name": "THEGREENHOUSE containment",
    "local_only": True, "remote_egress": "deny_except_fixed_local_ollama",
    "model_allowlist": "installed_ollama_models_only", "remote_tools": False,
    "autonomous_swarm": False, "repository_writes": False,
    "operator_stop_required": True, "approval_for_side_effects": "not_implemented_deny",
    "claims": "software gateway for SI research, not achieved superintelligence",
}
NODES = [
    ("stargate", "UNIVERSAL STARGATE", "control", "active"),
    ("brain", "GPT-DOUG", "router", "available"),
    ("ollama", "LOCAL OLLAMA", "inference", "probed"),
    ("sonoxo", "GPT-SONOXO", "interface", "conceptual"),
    ("xunia", "XUNIA", "knowledge", "conceptual"),
    ("zyra", "ZYRA", "execution", "not-connected"),
    ("greenhouse", "THEGREENHOUSE", "policy", "enforced"),
    ("fleet", "SONOXO FLEET", "repositories", "not-connected"),
    ("redpanda", "RED PANDA", "verification", "conceptual"),
    ("glassonion", "GLASS ONION", "audit", "conceptual"),
]
GRAPH = {
    "schema": "stargate.si.ontology.v1",
    "disclaimer": "This is an architectural map; conceptual nodes are not running services.",
    "nodes": [{"id": n, "label": label, "kind": kind, "status": status}
              for n, label, kind, status in NODES],
    "edges": [
        {"from": "stargate", "to": "brain", "relation": "selects advisory roles"},
        {"from": "stargate", "to": "ollama", "relation": "local inference only"},
        {"from": "stargate", "to": "greenhouse", "relation": "requires operator stop gate"},
        {"from": "brain", "to": "xunia", "relation": "conceptual ontology"},
        {"from": "stargate", "to": "sonoxo", "relation": "future interface federation"},
        {"from": "stargate", "to": "fleet", "relation": "future read-only inventory"},
        {"from": "greenhouse", "to": "zyra", "relation": "future authorization boundary"},
        {"from": "redpanda", "to": "glassonion", "relation": "future verification provenance"},
    ],
}
SYSTEM = (
    "You are UNIVERSAL STARGATE, a local engineering-research interface for GPT-DOUG. "
    "Treat SI as speculative superintelligence research, never as achieved autonomy. "
    "Focus on verifiable designs, evidence, tests, and operator control. "
    "The ontology graph is conceptual. You have no tools, internet, execution, "
    "or permission to modify files or deploy software. Do not claim those actions occurred. "
    "Never claim unsupported connections, consciousness, or capabilities. "
    "Only propose bounded actions for explicit independent operator review."
)


def roles_for(task: str) -> list[str]:
    """Existing GPT-DOUG advisory router; no agent processes spawned."""
    from gpt_brain.router import BrainRouter
    return [spec.name for spec in BrainRouter().route(task, max_agents=4)]


def _json_from(resp, max_bytes: int = 1024 * 1024) -> dict:
    raw = resp.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("upstream response too large")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("upstream JSON must be an object")
    return obj


def local_models() -> list[str]:
    req = Request(OLLAMA_API + "/api/tags", headers={"Accept": "application/json"})
    with urlopen(req, timeout=3) as resp:
        records = _json_from(resp).get("models", [])
    if not isinstance(records, list):
        raise ValueError("unexpected model inventory")
    return [x["name"] for x in records[:100] if isinstance(x, dict)
            and isinstance(x.get("name"), str) and MODEL_RE.fullmatch(x["name"])][:50]


def inference(model: str, messages: list[dict]) -> str:
    # Stop is checked before and after inference to ensure no stopped result is delivered.
    require_ai_allowed("stargate model inference")
    payload = json.dumps({"model": model, "stream": False,
                          "messages": [{"role": "system", "content": SYSTEM}] + messages,
                          "options": {"num_predict": 768}}).encode()
    req = Request(OLLAMA_API + "/api/chat", data=payload, method="POST",
                  headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urlopen(req, timeout=90) as resp:
        result = _json_from(resp, 2 * 1024 * 1024)
    require_ai_allowed("stargate reply delivery")
    message = result.get("message", {})
    answer = message.get("content") if isinstance(message, dict) else None
    if not isinstance(answer, str):
        raise ValueError("local model returned no text")
    return answer


def validate_chat(raw: object) -> tuple[str, list[dict], str]:
    if not isinstance(raw, dict):
        raise ValueError("request must be an object")
    model = raw.get("model", DEFAULT_MODEL)
    if not isinstance(model, str) or not MODEL_RE.fullmatch(model):
        raise ValueError("invalid local model name")
    messages = raw.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError("expected 1-12 messages")
    result = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") not in {"user", "assistant"}:
            raise ValueError("only user and assistant messages are allowed")
        content = msg.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE:
            raise ValueError("message must have 1-3000 characters")
        result.append({"role": msg["role"], "content": content})
    if result[-1]["role"] != "user":
        raise ValueError("final message must be from the user")
    return model, result, result[-1]["content"]


class Handler(BaseHTTPRequestHandler):
    server_version = "UniversalStargate/0.1"

    def _send(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; "
                         "script-src 'self'; style-src 'self'; connect-src 'self'; "
                         "img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def _reply(self, code: int, data: dict) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _valid_host(self) -> bool:
        port = self.server.server_port
        return self.headers.get("Host", "") in {
            "localhost", "127.0.0.1", f"localhost:{port}", f"127.0.0.1:{port}"}

    def _valid_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True  # Allows local curl; service is bound to loopback.
        try:
            u = urlsplit(origin)
        except ValueError:
            return False
        return (u.scheme == "http" and u.netloc == self.headers.get("Host")
                and not u.path and not u.query and not u.fragment)

    def do_GET(self):
        if not self._valid_host():
            self._reply(403, {"error": "loopback Host required"})
            return
        path = urlsplit(self.path).path
        if path == "/api/status":
            state = stop_status()
            self._reply(200, {"service": "UNIVERSAL STARGATE", "version": "0.1.0",
                              "mode": "local-read-only", "blocked": state["stopped"],
                              "stop_reason": state["reason"], "ollama": OLLAMA_API,
                              "autonomous_swarm": False})
        elif path == "/api/policy":
            self._reply(200, POLICY)
        elif path == "/api/ontology":
            self._reply(200, GRAPH)
        elif path == "/api/models":
            try:
                self._reply(200, {"connected": True, "models": local_models(),
                                  "default": DEFAULT_MODEL})
            except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
                self._reply(200, {"connected": False, "models": [],
                                  "default": DEFAULT_MODEL})
        else:
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/app.css": ("app.css", "text/css; charset=utf-8")}
            if path in assets:
                filename, mime = assets[path]
                try:
                    content = (STATIC / filename).read_bytes()
                except OSError:
                    self._reply(503, {"error": "static asset missing"})
                    return
                self._send(200, content, mime)
            else:
                self._reply(404, {"error": "unknown route"})

    def do_POST(self):
        if not self._valid_host() or not self._valid_origin():
            self._reply(403, {"error": "origin or host rejected"})
            return
        path = urlsplit(self.path).path
        if path not in {"/api/route", "/api/chat"}:
            self._reply(404, {"error": "unknown route"})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._reply(415, {"error": "JSON required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_INPUT:
            self._reply(413, {"error": "invalid request size"})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/api/route":
                if not isinstance(body, dict) or not isinstance(body.get("task"), str):
                    raise ValueError("task string required")
                task = body["task"].strip()
                if not 1 <= len(task) <= MAX_MESSAGE:
                    raise ValueError("task must be 1-3000 characters")
                self._reply(200, {"roles": roles_for(task), "mode": "advisory-only",
                                  "executed": False})
                return
            require_ai_allowed("stargate request")
            model, msgs, last = validate_chat(body)
            installed = local_models()  # Never forward arbitrary, uninstalled model names.
            if model not in installed:
                self._reply(400, {"error": f"model '{model}' is not installed; run ollama pull {model}"})
                return
            if not _MAX_PARALLEL_INFERENCE.acquire(blocking=False):
                self._reply(429, {"error": "two inference requests already running"})
                return
            try:
                result = inference(model, msgs)
            finally:
                _MAX_PARALLEL_INFERENCE.release()
            self._reply(200, {"reply": result, "model": model,
                              "roles": roles_for(last), "executed": False,
                              "provider": "local-ollama"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as error:
            self._reply(400, {"error": str(error)})
        except AIKillSwitchEngaged:
            self._reply(403, {"error": "operator AI emergency stop is active"})
        except HTTPError as error:
            self._reply(502, {"error": f"local Ollama HTTP {error.code}"})
        except (OSError, URLError, TimeoutError):
            self._reply(503, {"error": "Ollama unavailable; verify local service on 11434"})

    def log_message(self, fmt, *args):
        return  # Do not log chat content.


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Local Universal Stargate for SI research")
    parser.add_argument("--port", type=int, default=8799)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1-65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print(f"UNIVERSAL STARGATE READY http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
