"""Local-only Ollama transport: never calls a hosted model or remote URL."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request


class LocalModelError(RuntimeError):
    """Ollama is unavailable or returned an invalid response."""


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise LocalModelError("Ollama redirects are disabled")


class Ollama:
    def __init__(self, model: str = "gpt-doug-ttd", port: int = 11434):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?(?::[A-Za-z0-9_.-]+)?", model) or len(model) > 100:
            raise ValueError("invalid model name")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("invalid port")
        self.model, self.port = model, port
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectRedirects())

    def generate(self, prompt: str) -> str:
        from ai_killswitch import require_ai_allowed

        require_ai_allowed("TTD-LLM local model inference")
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/generate",
            data=json.dumps({"model": self.model, "prompt": prompt, "stream": False,
                             "options": {"temperature": 0}}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with self.opener.open(request, timeout=60) as response:
                raw = response.read(65_537)
            if len(raw) > 65_536:
                raise LocalModelError("Ollama response exceeds 64 KiB")
            content = json.loads(raw).get("response")
            if not isinstance(content, str) or not content.strip():
                raise LocalModelError("Ollama returned an empty response")
            return content.strip()
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise LocalModelError("Local Ollama unavailable or returned invalid data") from exc
