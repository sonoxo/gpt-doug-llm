#!/usr/bin/env python3
"""GPT-DOUG POCKET: USB-resident local-first assistant over llama.cpp.

The model server runs on the host CPU/GPU, while model cache, memory, workspace,
logs, and repository state can live on an external drive. No paid API is needed.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POCKET = Path(os.environ.get("GPT_DOUG_POCKET", ROOT)).resolve()
MEMORY = Path(os.environ.get("GPT_DOUG_MEMORY", POCKET / "memory"))
WORKSPACE = Path(os.environ.get("GPT_DOUG_WORKSPACE", POCKET / "workspace"))
BASE = os.environ.get("GPT_DOUG_API", "http://127.0.0.1:9931/v1").rstrip("/")
MEMORY.mkdir(parents=True, exist_ok=True)
WORKSPACE.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = MEMORY / "pocket-history.json"

SYSTEM = """You are GPT-DOUG POCKET, the local-first ZYRA assistant for GPT-DOUG-LLM.
You run against a local llama.cpp model with no paid API requirement. Be concise,
practical, and explicit about what was actually executed. Your persistent state,
workspace, model cache, and logs may live on the user's USB drive. Do not claim
background execution or external access you do not have. Keep actions bounded to
this assistant's own workspace/repository unless the user explicitly launches a
separate authorized tool. Prefer free, local, reversible workflows."""


def request_json(path: str, payload=None, timeout=120):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def model_name() -> str:
    data = request_json("/models", timeout=10)
    items = data.get("data") or []
    if not items:
        return os.environ.get("ZYRA_MODEL", "local-model")
    return str(items[0].get("id") or os.environ.get("ZYRA_MODEL", "local-model"))


def load_history():
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(history):
    # Keep persistent memory bounded for small local models.
    trimmed = history[-24:]
    HISTORY_FILE.write_text(json.dumps(trimmed, indent=2) + "\n", encoding="utf-8")


def git(*args):
    try:
        p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout.strip() or p.stderr.strip())
    except Exception as exc:
        return 1, str(exc)


def status(model: str):
    _, branch = git("branch", "--show-current")
    _, changes = git("status", "--short")
    print("\n🟣 GPT-DOUG POCKET")
    print(f"🧠 Model: {model}")
    print(f"🔌 API: {BASE}")
    print(f"💾 Pocket: {POCKET}")
    print(f"🧬 Memory: {HISTORY_FILE}")
    print(f"🛠️ Workspace: {WORKSPACE}")
    print(f"🌿 Branch: {branch or 'unknown'}")
    print(f"📝 Repo changes: {len([x for x in changes.splitlines() if x.strip()])}")
    print("💸 Paid API: OFF")
    print("⌨️ /status /fleet /files /memory /sync /clear /quit\n")


def fleet():
    agents = sorted(p.name for p in (ROOT / "agents").glob("*.py") if not p.name.startswith("__"))
    workers = sorted(p.name for p in (ROOT / "workers").rglob("*.py")) if (ROOT / "workers").exists() else []
    print(f"🤖 Fleet: {len(agents)} agent modules + {len(workers)} worker modules")
    if agents:
        print("   agents:", ", ".join(agents[:16]))
    if workers:
        print("   workers:", ", ".join(workers[:16]))


def chat(model: str, history, prompt: str) -> str:
    messages = [{"role": "system", "content": SYSTEM}] + history[-20:] + [{"role": "user", "content": prompt}]
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 512,
    }
    data = request_json("/chat/completions", payload, timeout=180)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(data.get("error") or "empty model response")
    return str((choices[0].get("message") or {}).get("content") or "").strip()


def main() -> int:
    try:
        model = model_name()
    except Exception as exc:
        print(f"❌ GPT-DOUG POCKET cannot reach local model server: {exc}")
        return 2

    history = load_history()
    status(model)
    while True:
        try:
            prompt = input("GPT-DOUG > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGPT-DOUG POCKET // session closed")
            return 0
        if not prompt:
            continue
        cmd = prompt.lower()
        if cmd in {"/quit", "/exit"}:
            return 0
        if cmd == "/status":
            status(model)
            continue
        if cmd == "/fleet":
            fleet()
            continue
        if cmd == "/files":
            files = sorted(str(p.relative_to(WORKSPACE)) for p in WORKSPACE.rglob("*") if p.is_file())
            print("📁 Workspace files:", ", ".join(files[:50]) if files else "empty")
            continue
        if cmd == "/memory":
            print(f"🧬 Persistent turns: {len(history)} // {HISTORY_FILE}")
            continue
        if cmd == "/clear":
            history = []
            save_history(history)
            print("🧹 Pocket conversation memory cleared.")
            continue
        if cmd == "/sync":
            code, dirty = git("status", "--porcelain")
            if code != 0:
                print("❌ Git unavailable.")
                continue
            if dirty.strip():
                print("⚠️ Repo has local changes; sync skipped to avoid overwriting work.")
                continue
            code, out = git("pull", "--ff-only")
            print(("✅ " if code == 0 else "❌ ") + (out or "sync complete"))
            continue

        try:
            answer = chat(model, history, prompt)
        except Exception as exc:
            print(f"❌ Local inference error: {exc}")
            continue
        print(answer)
        history.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ])
        save_history(history)


if __name__ == "__main__":
    raise SystemExit(main())
