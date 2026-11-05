"""GPT-Sonoxo: dependency-free, loopback-only local command center."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

STATIC = Path(__file__).with_name("static")
OLLAMA = "http://127.0.0.1:11434"
DEFAULT_MODEL = os.environ.get("GPT_SONOXO_MODEL", "qwen2.5:3b")
MAX_BODY = 64 * 1024
MAX_MESSAGES = 16
MAX_MESSAGE_LENGTH = 4096
MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,80}(?::[A-Za-z0-9][A-Za-z0-9._-]{0,30})?$")

ONTOLOGY = {
    "schema": "sonoxo.ontology.v1",
    "note": "Conceptual integration graph; nodes do not imply live services, permissions, or remote connectivity.",
    "nodes": [
        {"id": "gpt-sonoxo", "label": "GPT-SONOXO", "kind": "interface"},
        {"id": "gpt-doug", "label": "GPT-DOUG", "kind": "router"},
        {"id": "sonoxo-fleet", "label": "SONOXO FLEET", "kind": "inventory"},
        {"id": "xunia", "label": "XUNIA", "kind": "ontology"},
        {"id": "zyra", "label": "ZYRA", "kind": "bounded-execution"},
        {"id": "greenhouse", "label": "THEGREENHOUSE", "kind": "policy"},
        {"id": "ollama", "label": "OLLAMA", "kind": "local-inference"},
    ],
    "edges": [
        {"from": "gpt-sonoxo", "to": "gpt-doug", "type": "routes-task"},
        {"from": "gpt-sonoxo", "to": "ollama", "type": "requests-inference"},
        {"from": "gpt-doug", "to": "sonoxo-fleet", "type": "references-inventory"},
        {"from": "gpt-doug", "to": "xunia", "type": "uses-ontology-concepts"},
        {"from": "gpt-doug", "to": "zyra", "type": "proposes-controlled-action"},
        {"from": "zyra", "to": "greenhouse", "type": "requires-policy-gate"},
    ],
}
SYSTEM = """You are GPT-SONOXO, the local open-source Sonoxo engineering assistant.
Assist with GPT-DOUG, XUNIA, ZYRA, THEGREENHOUSE, and Sonoxo Fleet.
Be precise. Distinguish verified evidence, inference and proposed changes.
This is a read-only chat interface: you cannot edit repositories, launch agents,
run tools, deploy software, or claim integrations are connected.
Do not invent live statuses, credentials, citations, or test results.
For consequential actions, describe explicit approval and test requirements.
"""

def blocked() -> bool:
    return os.environ.get("GPT_DOUG_AI_BLOCK_ALL", "").strip().lower() in {"1", "true", "yes", "on"}

def roles_for(prompt: str) -> list[str]:
    """Use the existing GPT-DOUG role router without executing any agents."""
    from gpt_brain.router import BrainRouter
    return [spec.name for spec in BrainRouter().route(prompt, max_agents=4)]

def _read_json(response, limit: int = 512 * 1024) -> dict:
    raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("local inference reply exceeded size limit")
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("local inference returned an invalid JSON object")
    return payload

def local_models() -> list[str]:
    request = Request(OLLAMA + "/api/tags", headers={"Accept": "application/json"})
    with urlopen(request, timeout=3) as response:
        payload = _read_json(response)
    entries = payload.get("models", [])
    if not isinstance(entries, list):
        raise ValueError("invalid model inventory")
    return [x["name"] for x in entries if isinstance(x, dict)
            and isinstance(x.get("name"), str) and MODEL_NAME.fullmatch(x["name"])][:50]

def _ollama_chat(model: str, messages: list[dict]) -> str:
    data = json.dumps({"model": model, "messages": messages, "stream": False,
                       "options": {"num_predict": 1024}}).encode("utf-8")
    request = Request(OLLAMA + "/api/chat", data=data,
                      headers={"Content-Type": "application/json", "Accept": "application/json"},
                      method="POST")
    with urlopen(request, timeout=120) as response:
        payload = _read_json(response, 2 * 1024 * 1024)
    message = payload.get("message")
    answer = message.get("content") if isinstance(message, dict) else None
    if not isinstance(answer, str):
        raise ValueError("local inference response has no text")
    return answer

def _validate_chat(payload: object) -> tuple[str, list[dict], str]:
    if not isinstance(payload, dict):
        raise ValueError("request must be a JSON object")
    model = payload.get("model", DEFAULT_MODEL)
    if not isinstance(model, str) or not MODEL_NAME.fullmatch(model):
        raise ValueError("invalid local model name")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError("messages must contain between 1 and 16 turns")
    cleaned = []
    for item in messages:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise ValueError("only user and assistant turns are accepted")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip() or len(content) > MAX_MESSAGE_LENGTH:
            raise ValueError("message content is empty or too long")
        cleaned.append({"role": item["role"], "content": content})
    if cleaned[-1]["role"] != "user":
        raise ValueError("last message must be from the user")
    return model, cleaned, cleaned[-1]["content"]

class Handler(BaseHTTPRequestHandler):
    server_version = "GPTSonoxo/0.1"

    def _send(self, status: int, body: bytes, mime: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data: dict) -> None:
        self._send(code, json.dumps(data).encode("utf-8"), "application/json; charset=utf-8")

    def _allowed_host(self) -> bool:
        host = self.headers.get("Host", "")
        port = self.server.server_port
        return host in {"127.0.0.1", "localhost", "[::1]",
                        f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}

    def _allowed_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            url = urlsplit(origin)
            return url.scheme == "http" and url.netloc == self.headers.get("Host") and url.path == ""
        except ValueError:
            return False

    def do_GET(self) -> None:
        if not self._allowed_host():
            self._json(403, {"error": "loopback host required"})
            return
        if self.path == "/api/health":
            self._json(200, {"app": "gpt-sonoxo", "version": "0.1.0", "local_only": True,
                             "blocked": blocked(), "model": DEFAULT_MODEL})
            return
        if self.path == "/api/ontology":
            self._json(200, ONTOLOGY)
            return
        if self.path == "/api/models":
            try:
                self._json(200, {"models": local_models(), "default": DEFAULT_MODEL,
                                 "engine": "ollama", "connected": True})
            except (HTTPError, URLError, TimeoutError, ValueError, OSError):
                self._json(200, {"models": [], "default": DEFAULT_MODEL,
                                 "engine": "ollama", "connected": False})
            return
        assets = {"/": ("index.html", "text/html; charset=utf-8"),
                  "/app.css": ("app.css", "text/css; charset=utf-8"),
                  "/app.js": ("app.js", "text/javascript; charset=utf-8")}
        if self.path in assets:
            name, mime = assets[self.path]
            self._send(200, (STATIC / name).read_bytes(), mime)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._allowed_host() or not self._allowed_origin():
            self._json(403, {"error": "cross-origin or non-loopback request rejected"})
            return
        if self.path != "/api/chat":
            self._json(404, {"error": "not found"})
            return
        if blocked():
            self._json(403, {"error": "operator kill switch is active"})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            self._json(415, {"error": "application/json required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self._json(413, {"error": "request exceeds size limit or is empty"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            model, history, latest = _validate_chat(payload)
            roles = roles_for(latest)
            system = SYSTEM + "\nRelevant advisory specialties: " + ", ".join(roles)
            reply = _ollama_chat(model, [{"role": "system", "content": system}] + history)
            self._json(200, {"reply": reply, "model": model, "routed_roles": roles,
                             "execution": "none", "source": "local_ollama"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except HTTPError as exc:
            self._json(502, {"error": f"Ollama returned HTTP {exc.code}; verify model is installed"})
        except (URLError, TimeoutError, OSError) as exc:
            self._json(503, {"error": "Ollama unavailable. Run ollama serve and pull a local model.",
                             "details": type(exc).__name__})

    def log_message(self, fmt, *args):
        return  # Do not log chat prompts.

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="gpt-sonoxo", description="Local Sonoxo AI command center")
    parser.add_argument("--port", type=int, default=8765, help="loopback port (default: 8765)")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    print(f"GPT-SONOXO ready: http://127.0.0.1:{args.port} (local-only)", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
