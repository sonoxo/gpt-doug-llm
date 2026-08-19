#!/usr/bin/env python3
"""Responsive local-only ZYRA terminal chat for GPT-DOUG-LLM."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from zyra import Zyra

ROOT = Path(__file__).resolve().parent
BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
REQUESTED_MODEL = (
    os.environ.get("ZYRA_MODEL")
    or os.environ.get("OLLAMA_MODEL")
    or os.environ.get("GPT_DOUG_FAST_MODEL")
    or "gpt-doug"
)
TIMEOUT = float(os.environ.get("ZYRA_TIMEOUT", "90"))
MAX_TURNS = max(2, int(os.environ.get("ZYRA_MAX_TURNS", "12")))

SYSTEM = """You are ZYRA, the responsive local conversational assistant for GPT-DOUG-LLM.
Answer ordinary user messages directly and naturally.
Never reply with PASS or BLOCKED unless the deterministic local policy layer actually produced that status.
Do not claim background work, consciousness, government authority, or access you do not have.
The "fleet" means local agent/orchestration code in this repository, not a physical location.
Keep one user message to one bounded model response. No recursive self-calls or autonomous loops.
When a request requires external or privileged action, explain what would be needed instead of pretending it happened.
"""


def _json_request(path: str, body: dict | None = None, timeout: float | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout or TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def installed_models() -> list[str]:
    data = _json_request("/api/tags", timeout=4)
    return [item.get("name", "") for item in data.get("models", []) if item.get("name")]


def choose_model(models: list[str]) -> str:
    if not models:
        raise RuntimeError("No Ollama models are installed.")
    for wanted in (REQUESTED_MODEL, "gpt-doug", "qwen2.5-coder", "qwen2.5"):
        for name in models:
            if name == wanted or name.startswith(wanted + ":"):
                return name
    return models[0]


def git_run(*args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=4,
        )
        text = result.stdout.strip() or result.stderr.strip()
        return result.returncode, text
    except Exception:
        return 1, "unavailable"


def show_dashboard(model: str) -> None:
    branch_rc, branch_text = git_run("branch", "--show-current")
    status_rc, status_text = git_run("status", "--short")
    branch = branch_text if branch_rc == 0 and branch_text else "unknown"
    changed = (
        len([line for line in status_text.splitlines() if line.strip()])
        if status_rc == 0
        else "?"
    )
    print("\n🟣 ZYRA // GPT-DOUG-LLM")
    print(f"🧠 Model: {model}")
    print(f"🌿 Branch: {branch}")
    print(f"📝 Working tree: {changed} changed")
    print("🛡️ Mode: local chat // one response per message // no recursive loop")
    print("⌨️  Commands: /help /status /fleet /xunia /clear /quit\n")


def show_fleet() -> None:
    agents = sorted(p.name for p in (ROOT / "agents").glob("*.py") if not p.name.startswith("__"))
    workers_dir = ROOT / "workers"
    workers = sorted(p.name for p in workers_dir.rglob("*.py")) if workers_dir.exists() else []
    print(f"🤖 Fleet inventory: {len(agents)} agent modules + {len(workers)} worker modules")
    if agents:
        print("   agents:", ", ".join(agents[:12]))
    if workers:
        print("   workers:", ", ".join(workers[:12]))


def main() -> int:
    zyra = Zyra()
    try:
        models = installed_models()
        model = choose_model(models)
    except Exception as exc:
        print(f"ZYRA OFFLINE // Ollama check failed: {exc}")
        print("Start Ollama and confirm at least one local model is installed.")
        return 1

    show_dashboard(model)
    history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM}]

    while True:
        try:
            prompt = input("ZYRA > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nZYRA // session closed")
            return 0
        if not prompt:
            continue

        command = prompt.lower()
        if command in {"/quit", "/exit"}:
            return 0
        if command == "/help":
            print("/help /status /fleet /xunia /dashboard /clear /quit")
            continue
        if command in {"/status", "/xunia", "/dashboard"}:
            show_dashboard(model)
            continue
        if command == "/fleet":
            show_fleet()
            continue
        if command == "/clear":
            history = [{"role": "system", "content": SYSTEM}]
            print("🧹 Conversation memory cleared.")
            continue

        verdict = zyra.inspect(prompt, "input")
        if not verdict.allowed:
            print("ZYRA BLOCKED // " + "; ".join(verdict.reasons))
            continue

        history.append({"role": "user", "content": verdict.text})
        request_history = history[:1] + history[-(MAX_TURNS * 2):]
        try:
            result = _json_request(
                "/api/chat",
                {
                    "model": model,
                    "messages": request_history,
                    "stream": False,
                    "options": {"temperature": 0.35},
                },
            )
            answer = (result.get("message") or {}).get("content", "").strip()
            if not answer:
                error = result.get("error") or result.get("done_reason") or "empty model response"
                print(f"ZYRA ERROR // {error}")
                continue
        except urllib.error.HTTPError as exc:
            print(f"ZYRA ERROR // Ollama HTTP {exc.code}")
            continue
        except urllib.error.URLError:
            print("ZYRA ERROR // Ollama became unreachable")
            continue
        except TimeoutError:
            print("ZYRA ERROR // model response timed out")
            continue
        except Exception as exc:
            print(f"ZYRA ERROR // {type(exc).__name__}: {exc}")
            continue

        output = zyra.inspect(answer, "output")
        if not output.allowed:
            print("ZYRA OUTPUT BLOCKED // " + "; ".join(output.reasons))
            continue

        print(output.text)
        history.append({"role": "assistant", "content": output.text})


if __name__ == "__main__":
    raise SystemExit(main())
