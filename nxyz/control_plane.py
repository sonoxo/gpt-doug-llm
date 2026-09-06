#!/usr/bin/env python3
"""GPT-DOUG-LLM-MAX NXYZ cloud control-plane adapter.

The adapter is deliberately provider-neutral: GitHub remains source of truth while
an operator-configured NXYZ webhook can receive signed-by-transport lifecycle data.
No secret is stored in the repository.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("nxyz/out")


def payload(kind: str) -> dict[str, object]:
    return {
        "schema": "xunia.nxyz.agent-event.v1",
        "kind": kind,
        "agent": "gpt-doug-llm-max",
        "platform": "xunia-hub",
        "source_of_truth": "github",
        "repository": os.getenv("GITHUB_REPOSITORY", "sonoxo/gpt-doug-llm"),
        "sha": os.getenv("GITHUB_SHA", "local"),
        "ref": os.getenv("GITHUB_REF", "local"),
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "event": os.getenv("GITHUB_EVENT_NAME", "manual"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "policy": "guarded-auto-upgrade",
    }


def emit(kind: str) -> int:
    data = payload(kind)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "status.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    url = os.getenv("NXYZ_WEBHOOK_URL", "").strip()
    token = os.getenv("NXYZ_WEBHOOK_TOKEN", "").strip()
    if not url:
        print("NXYZ webhook not configured; local control-plane artifact written.")
        return 0

    headers = {"Content-Type": "application/json", "User-Agent": "gpt-doug-llm-max/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"NXYZ webhook returned HTTP {response.status}")
        print("NXYZ control-plane event delivered.")
        return 0
    except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
        print(f"NXYZ delivery failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(emit(sys.argv[1] if len(sys.argv) > 1 else "heartbeat"))
