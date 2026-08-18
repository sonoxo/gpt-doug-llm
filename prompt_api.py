#!/usr/bin/env python3
"""Open-source prompt-to-app REST API.

A small, dependency-free service that turns a natural-language app description
into source files using a local Ollama-compatible model. No paid API is required.
Generated projects are written only under PROMPT_APP_WORKSPACE.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HOST = os.environ.get("PROMPT_APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("PROMPT_APP_PORT", "8790"))
WORKSPACE = Path(os.environ.get("PROMPT_APP_WORKSPACE", "./prompt-app-projects")).resolve()
OLLAMA_URL = os.environ.get("PROMPT_APP_OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODEL = os.environ.get("PROMPT_APP_MODEL", "qwen2.5-coder:7b")
MAX_BODY = 256 * 1024
MAX_PROMPT = 12_000
MAX_FILES = 64
MAX_FILE_BYTES = 512 * 1024
NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

SYSTEM = """You are an expert software generator. Turn the user's product idea into a small,
working, locally-runnable MVP. Respond with JSON only, matching this schema:
{
  "name": "project-name",
  "summary": "one sentence",
  "stack": ["..."],
  "run": "single local run command",
  "files": [{"path": "relative/path", "content": "complete file contents"}]
}
Rules: use only relative paths; never emit secrets; prefer minimal dependencies; include a README;
for browser apps include an index.html; do not wrap JSON in markdown fences.
"""


def _json_from_model(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ValueError("model response must contain a files array")
    return data


def _safe_relpath(raw: str) -> Path:
    if not isinstance(raw, str) or not raw or raw.startswith(("/", "\\")):
        raise ValueError("invalid file path")
    p = Path(raw)
    if any(part in ("", ".", "..") for part in p.parts):
        raise ValueError(f"unsafe file path: {raw}")
    return p


def _project_dir(name: str) -> Path:
    if not NAME_RE.fullmatch(name or ""):
        raise ValueError("project name must use letters, numbers, - or _")
    root = WORKSPACE.resolve()
    target = (root / name).resolve()
    if root not in target.parents:
        raise ValueError("project path escaped workspace")
    return target


def _call_local_model(prompt: str) -> dict:
    payload = {
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"local model unavailable at {OLLAMA_URL}; start Ollama and install {MODEL}"
        ) from exc
    content = ((body.get("message") or {}).get("content") or "").strip()
    if not content:
        raise RuntimeError("local model returned no content")
    return _json_from_model(content)


def materialize(spec: dict, requested_name: str | None = None) -> dict:
    name = requested_name or str(spec.get("name") or f"app-{uuid.uuid4().hex[:8]}")
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-")[:64] or f"app-{uuid.uuid4().hex[:8]}"
    target = _project_dir(name)
    target.mkdir(parents=True, exist_ok=True)

    files = spec.get("files", [])
    if len(files) > MAX_FILES:
        raise ValueError(f"too many files; maximum is {MAX_FILES}")

    written = []
    for item in files:
        rel = _safe_relpath(item.get("path", ""))
        content = item.get("content", "")
        if not isinstance(content, str):
            raise ValueError(f"content for {rel} must be text")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            raise ValueError(f"file too large: {rel}")
        dest = (target / rel).resolve()
        if target not in dest.parents:
            raise ValueError(f"unsafe file path: {rel}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(encoded)
        written.append(rel.as_posix())

    metadata = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "summary": spec.get("summary", ""),
        "stack": spec.get("stack", []),
        "run": spec.get("run", ""),
        "files": written,
        "created_at": int(time.time()),
    }
    (target / ".prompt-app.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_BODY:
            raise ValueError("request too large")
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON") from exc

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/health":
            return self._send(200, {"ok": True, "model": MODEL, "workspace": str(WORKSPACE)})
        if path == "/projects":
            WORKSPACE.mkdir(parents=True, exist_ok=True)
            projects = sorted(p.name for p in WORKSPACE.iterdir() if p.is_dir())
            return self._send(200, {"projects": projects})
        match = re.fullmatch(r"/projects/([^/]+)", path)
        if match:
            try:
                root = _project_dir(match.group(1))
            except ValueError as exc:
                return self._send(400, {"error": str(exc)})
            meta = root / ".prompt-app.json"
            if not meta.is_file():
                return self._send(404, {"error": "project not found"})
            return self._send(200, json.loads(meta.read_text(encoding="utf-8")))
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/generate":
            return self._send(404, {"error": "not found"})
        try:
            payload = self._read_json()
            prompt = str(payload.get("prompt", "")).strip()
            requested_name = payload.get("name")
            if not prompt:
                return self._send(400, {"error": "prompt is required"})
            if len(prompt) > MAX_PROMPT:
                return self._send(400, {"error": f"prompt exceeds {MAX_PROMPT} characters"})
            spec = _call_local_model(prompt)
            meta = materialize(spec, requested_name=requested_name)
            return self._send(201, {"ok": True, "project": meta})
        except ValueError as exc:
            return self._send(400, {"error": str(exc)})
        except RuntimeError as exc:
            return self._send(503, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return self._send(500, {"error": f"generation failed: {exc}"})


def main():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Prompt-to-App API listening on http://{HOST}:{PORT}")
    print(f"Local model: {MODEL} via {OLLAMA_URL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
