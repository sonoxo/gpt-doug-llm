from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from va3lm.planner import build_plan


def _allowed_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost"}


def ask(prompt: str) -> dict:
    text = prompt.strip()
    if not text:
        raise ValueError("prompt is required")
    base_url = os.getenv("VA3LM_MODEL_URL", "").rstrip("/")
    model = os.getenv("VA3LM_MODEL_NAME", "gpt-doug-llm")
    if not base_url:
        return {"mode": "DETERMINISTIC_PLAN", "model": model, "result": build_plan(text)}
    if not _allowed_url(base_url):
        return {"mode": "MODEL_URL_HOLD", "model": model, "error": "VA3LM_MODEL_URL must be localhost", "result": build_plan(text)}

    system_policy = (
        "You are VA3LM, the VIRGINIA execution/reasoning layer inside the XUNIAverse rooted at sonoxo/xuniadao. "
        "Operate defensively. Treat autonomous agents as first-class identities. Prefer SPIFFE-style identity, short-lived "
        "credentials, DPoP or mTLS token binding, least-privilege scopes, centralized auth brokering, explicit separation "
        "between an agent's own authority and user-delegated authority, runtime guardrails, and provenance-bearing audit "
        "evidence. Never expose or request shared or long-lived secrets for agents. Broad project or organization grants, "
        "repository mutation, external communication, production deployment, credential changes, and other consequential "
        "actions require human review. Do not claim Google Cloud, Palantir, government, or vendor deployment/endorsement "
        "without evidence. Produce safe, testable programming guidance and never claim execution unless evidence is provided."
    )

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_policy},
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = os.getenv("VA3LM_MODEL_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{base_url}/chat/completions", data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 - localhost allowlist enforced above
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"mode": "MODEL_ERROR_FALLBACK", "model": model, "error": type(exc).__name__, "result": build_plan(text)}
    return {"mode": "MODEL", "model": model, "result": body}
