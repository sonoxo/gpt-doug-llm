"""
Gemini API integration for GPT Doug — satisfies mandatory requirement #1.
Uses Google's Gemini API as an optional GPT Doug provider.

Setup:
  1. Get free Google Cloud account
  2. Request $150 credits on hackathon Resources tab
  3. Enable Gemini API in Google Cloud Console
  4. Set GEMINI_API_KEY environment variable

Usage:
  from google.gemini_backend import GeminiBackend

  gemini = GeminiBackend()
  response = gemini.chat([{"role": "user", "content": "Build a web app"}])
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

@dataclass
class GeminiConfig:
    api_key: str = ""
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 8192

class GeminiBackend:
    """Gemini API backend for the normalized agent-chain contract.
    
    Same interface as agents/llm_backend.py so agent_chain.py works
    with any provider supported by the shared facade.
    """

    def __init__(self, config: GeminiConfig | None = None):
        self.config = config or GeminiConfig()
        self.config.api_key = self.config.api_key or GEMINI_API_KEY
        if not self.config.api_key:
            raise ValueError("Set GEMINI_API_KEY environment variable")

    def chat_once(self, messages: list, model: str | None = None, options: dict | None = None) -> dict:
        """Non-streaming chat. Returns the shared normalized event shape."""
        contents = self._convert_messages(messages)
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": (options or {}).get("temperature", self.config.temperature),
                "maxOutputTokens": (options or {}).get("max_tokens", self.config.max_tokens),
            },
        }
        request = urllib.request.Request(
            f"{GEMINI_URL}?key={self.config.api_key}",
            json.dumps(body).encode(),
            {"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read())
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            # Return the normalized event shape used by agent_chain.
            return {"message": {"role": "assistant", "content": text}, "done": True}
        except urllib.error.URLError as e:
            return {"message": {"role": "assistant", "content": f"Gemini API error: {e}"}, "done": True, "error": str(e)}

    def _convert_messages(self, messages: list) -> list:
        """Convert the shared message format to Gemini format."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Gemini uses "user" and "model" (not "assistant")
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
        return contents

    def health(self) -> dict:
        return {
            "backend": "gemini",
            "model": self.config.model,
            "api_key_set": bool(self.config.api_key),
            "url": GEMINI_URL,
        }


def auto_select_backend() -> dict:
    """Automatically select the best available backend.
    Priority: an explicitly configured cloud provider, otherwise offline.
    """
    if os.environ.get("GEMINI_API_KEY"):
        return {"backend": "gemini", "config": GeminiConfig()}
    if os.environ.get("OPENAI_API_KEY"):
        return {"backend": "openai"}
    return {"backend": "none"}


if __name__ == "__main__":
    print(json.dumps(auto_select_backend(), indent=2, default=str))
    if GEMINI_API_KEY:
        print("\nGemini backend ready. Set GEMINI_API_KEY to enable.")
    else:
        print("\nNo GEMINI_API_KEY set. Get one from Google Cloud Console.")
        print("Enable Generative Language API → Create API key → export GEMINI_API_KEY=...")
