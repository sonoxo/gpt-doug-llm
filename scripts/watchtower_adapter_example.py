"""Reference adapter for an operator-authorized AI runtime.

This script only checks an event; it does not invoke any model or tool.
Fail closed if the gateway is unavailable.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

GATEWAY = "http://127.0.0.1:8877/api/v1/evaluate"


def guard_before_action(model_ingest_token: str, intent: dict) -> bool:
    payload = json.dumps(intent).encode("utf-8")
    request = urllib.request.Request(GATEWAY, data=payload, headers={
        "Authorization": "Bearer " + model_ingest_token,
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            data = json.load(response)
            return response.status == 200 and data.get("verdict") == "allow" and data.get("enforce") is True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


if __name__ == "__main__":
    token = os.environ.get("WATCHTOWER_MODEL_INGEST_TOKEN", "")
    if not token:
        print("Set WATCHTOWER_MODEL_INGEST_TOKEN from an operator enrollment; refusing execution.", file=sys.stderr)
        raise SystemExit(3)
    sample = {"model_id": "llama3:8b", "provider": "ollama", "agent_id": "approved-agent",
              "kind": "inference", "action": "chat", "scope": "public", "content": "Hello"}
    allowed = guard_before_action(token, sample)
    print("ALLOW" if allowed else "DENY")
    raise SystemExit(0 if allowed else 3)
