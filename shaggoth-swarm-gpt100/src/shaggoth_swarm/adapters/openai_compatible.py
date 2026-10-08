from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ModelAdapter
from ..models import AgentSpec, SwarmTask


class OpenAICompatibleAdapter(ModelAdapter):
    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 60.0) -> None:
        if not model:
            raise ValueError("SHAGGOTH_MODEL is required for the openai-compatible adapter")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for the openai-compatible adapter")

    def complete(self, agent: AgentSpec, task: SwarmTask) -> str:
        body={"model":self.model,"messages":[{"role":"system","content":f"You are a bounded {agent.specialty} specialist. Complete only the assigned task."},{"role":"user","content":task.prompt}]}
        request=Request(f"{self.base_url}/chat/completions",data=json.dumps(body).encode("utf-8"),headers={"authorization":f"Bearer {self.api_key}","content-type":"application/json"},method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload=json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"model request failed: {exc}") from exc
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("model response did not contain choices[0].message.content") from exc
