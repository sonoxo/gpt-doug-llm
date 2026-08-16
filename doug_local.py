#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from mlx_lm import load, generate

ROOT = Path(__file__).resolve().parent
MODEL = os.getenv(
    "DOUG_LOCAL_MODEL",
    "mlx-community/Llama-3.2-3B-Instruct-4bit",
)

SYSTEM = """
You are GPT-Doug, a local vibe-coding engineering agent.

The user's natural language IS the programming specification.

OPERATING METHOD:
1. Understand what the user wants.
2. Inspect supplied repository context.
3. Preserve existing work.
4. Make the smallest useful implementation.
5. Never use Ollama.
6. Never use localhost:11434.
7. Prefer working code over explanations.
8. Test modifications.
9. Do not delete unrelated functionality.
10. Stay inside the current repository.

When code changes are required, return ONLY valid JSON:

{
  "message": "short explanation",
  "writes": [
    {
      "path": "relative/path/to/file",
      "content": "complete replacement file content"
    }
  ],
  "tests": [
    "python3 -m pytest -q"
  ]
}

If no file change is required:

{
  "message": "answer",
  "writes": [],
  "tests": []
}
""".strip()

ALLOWED_TEST_PREFIXES = (
    "python3 -m pytest",
    "python -m pytest",
    "python3 -m py_compile",
    "python -m py_compile",
    "node --check",
    "git diff --check",
    "git status",
)

DENIED = {
    ".git",
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
}


def shell(cmd):
    try:
        return subprocess.check_output(
            cmd,
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=20,
        ).strip()
    except Exception as exc:
        return f"<error: {exc}>"


def tree():
    result = shell([
        "find", ".",
        "-maxdepth", "3",
        "-type", "f",
        "-not", "-path", "./.git/*",
        "-not", "-path", "./node_modules/*",
        "-not", "-path", "./.venv-mlx/*",
    ])
    return "\n".join(result.splitlines()[:250])


def relevant_files(prompt):
    p = prompt.lower()

    candidates = []

    mappings = [
        (
            ("frontend", "ui", "dashboard", "interface", "page", "preview"),
            ["web/index.html", "web/app.js", "web/app.css"],
        ),
        (
            ("backend", "server", "api", "endpoint"),
            ["web/server.py"],
        ),
        (
            ("security", "heat seek", "cia", "turtle shell"),
            ["heatseek.py", "doug_core/heat_seek.py"],
        ),
        (
            ("vibe", "language", "prompt", "command"),
            ["vibe.py", "doug_core/vibe_language.py"],
        ),
        (
            ("agent", "worker"),
            ["agents/agent_chain.py", "web/worker.py"],
        ),
        (
            ("memory",),
            ["doug_core/memory.py"],
        ),
    ]

    for words, paths in mappings:
        if any(word in p for word in words):
            candidates.extend(paths)

    candidates.extend([
        "README.md",
        "pyproject.toml",
    ])

    seen = set()
    output = []

    for rel in candidates:
        if rel in seen:
            continue

        seen.add(rel)
        path = ROOT / rel

        if not path.exists() or not path.is_file():
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            if len(text) <= 30000:
                output.append(
                    f"\n===== FILE: {rel} =====\n{text}"
                )
        except Exception:
            pass

    return "\n".join(output)


def safe_path(rel):
    if not rel or rel.startswith("/"):
        return None

    candidate = (ROOT / rel).resolve()

    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None

    parts = set(candidate.relative_to(ROOT).parts)

    if parts & DENIED:
        return None

    if ".git" in parts or ".venv-mlx" in parts:
        return None

    return candidate


def parse_json(text):
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end < start:
        raise ValueError("Model did not return JSON.")

    return json.loads(text[start:end + 1])


def backup(path):
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    destination = (
        ROOT
        / ".doug"
        / "backups"
        / stamp
        / path.relative_to(ROOT)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(path, destination)


def apply(result):
    writes = result.get("writes", [])

    for change in writes:
        rel = change.get("path", "")
        content = change.get("content", "")

        path = safe_path(rel)

        if path is None:
            print(f"BLOCKED unsafe path: {rel}")
            continue

        backup(path)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            content,
            encoding="utf-8",
        )

        print(f"✓ wrote {rel}")

    for command in result.get("tests", []):
        if not command.startswith(ALLOWED_TEST_PREFIXES):
            print(f"BLOCKED command: {command}")
            continue

        print(f"\n$ {command}")

        proc = subprocess.run(
            command,
            cwd=ROOT,
            shell=True,
            text=True,
        )

        print(f"exit={proc.returncode}")


print()
print("==============================================")
print(" GPT-DOUG LOCAL VIBE CODER")
print(" MLX • NO OLLAMA • NO API")
print("==============================================")
print()
print("Loading:", MODEL)
print("First launch downloads the model once.")
print()

model, tokenizer = load(MODEL)

print("GPT-Doug ready.")
print('Example: "make the dashboard look more modern"')
print('Type "exit" to quit.')
print()

while True:
    try:
        user = input("doug> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break

    if not user:
        continue

    if user.lower() in {"exit", "quit"}:
        break

    context = f"""
REPOSITORY:
{ROOT}

GIT:
{shell(["git", "status", "--short"])}

FILES:
{tree()}

RELEVANT SOURCE:
{relevant_files(user)}

USER VIBE COMMAND:
{user}
""".strip()

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": context},
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False,
    )

    print("\nDoug is coding...\n")

    answer = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=1800,
        verbose=False,
    )

    try:
        result = parse_json(answer)

        print(result.get("message", ""))
        apply(result)

        print("\n--- git status ---")
        print(shell(["git", "status", "--short"]))
        print()

    except Exception as exc:
        print("Could not auto-apply:", exc)
        print()
        print(answer)
        print()

