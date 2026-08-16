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
MODEL_NAME = os.getenv(
    "DOUG_LOCAL_MODEL",
    "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
)

MAX_STEPS = 12

SYSTEM = """
You are GPT-Doug, a LOCAL autonomous vibe-coding agent.

The user's natural-language direction is the product specification.

LOOP:
inspect -> decide -> edit -> test -> observe -> repair -> verify

Return EXACTLY ONE JSON object per turn.

Allowed actions:

{"action":"read","path":"relative/file.py"}

{"action":"replace","path":"relative/file.py","find":"exact old text","replace":"new text"}

{"action":"write","path":"relative/new_file.py","content":"complete file"}

{"action":"shell","command":"python -m pytest -q"}

{"action":"finish","summary":"what was completed","verify":"python -m pytest -q"}

RULES:
- Make real code changes when the user asks to build/fix/upgrade/add/change something.
- Inspect files before changing unfamiliar code.
- Preserve existing work.
- Prefer replace over rewriting large existing files.
- Never use Ollama.
- Never use port 11434.
- Never access secrets.
- Never modify .git.
- Never claim success without verification.
- If a test fails, repair the failure.
- Do not output markdown.
- Do not output explanations outside the JSON object.
""".strip()

BLOCKED_PATH_PARTS = {
    ".git",
    ".venv-mlx",
    ".venv",
    "node_modules",
}

BLOCKED_FILES = {
    ".env",
    ".env.local",
    "credentials.json",
    "secrets.json",
}

SAFE_SHELL_PREFIXES = (
    "pwd",
    "ls",
    "find ",
    "rg ",
    "grep ",
    "sed -n ",
    "head ",
    "tail ",
    "git status",
    "git diff",
    "git branch",
    "git log",
    "python -m pytest",
    "python3 -m pytest",
    "python -m py_compile",
    "python3 -m py_compile",
    "node --check",
)


def safe_path(rel: str):
    if not rel or rel.startswith("/"):
        return None

    path = (ROOT / rel).resolve()

    try:
        relative = path.relative_to(ROOT.resolve())
    except ValueError:
        return None

    if any(part in BLOCKED_PATH_PARTS for part in relative.parts):
        return None

    if path.name in BLOCKED_FILES:
        return None

    return path


def backup(path: Path):
    if not path.exists():
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = ROOT / ".doug" / "backups" / stamp / path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def parse_json(text: str):
    text = text.strip()

    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")

    if start < 0:
        raise ValueError("No JSON object found")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape:
            escape = False
            continue

        if ch == "\\" and in_string:
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1

            if depth == 0:
                return json.loads(text[start:i + 1])

    raise ValueError("Incomplete JSON object")


def repo_map():
    result = subprocess.run(
        [
            "find", ".",
            "-maxdepth", "3",
            "-type", "f",
            "-not", "-path", "./.git/*",
            "-not", "-path", "./.venv-mlx/*",
            "-not", "-path", "./node_modules/*",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    return "\n".join(result.stdout.splitlines()[:400])


def git_status():
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    return result.stdout[-6000:] or "(clean)"


def run_shell(command: str):
    command = command.strip()

    if not command.startswith(SAFE_SHELL_PREFIXES):
        return {
            "exit": 126,
            "stdout": "",
            "stderr": "BLOCKED: command outside safe allowlist",
        }

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            shell=True,
            capture_output=True,
            text=True,
            timeout=180,
        )

        return {
            "exit": result.returncode,
            "stdout": result.stdout[-10000:],
            "stderr": result.stderr[-10000:],
        }

    except subprocess.TimeoutExpired:
        return {
            "exit": 124,
            "stdout": "",
            "stderr": "Command timed out",
        }


print()
print("======================================================")
print(" GPT-DOUG LOCAL VIBE AGENT")
print(" QWEN CODER • MLX • NO OLLAMA • NO API")
print("======================================================")
print()
print("Loading:", MODEL_NAME)

model, tokenizer = load(MODEL_NAME)

print()
print("READY")
print("Your sentence is the coding command.")
print("Type exit to quit.")
print()


def ask(messages):
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    return generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=1200,
        verbose=False,
    )


while True:
    try:
        objective = input("doug> ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        break

    if not objective:
        continue

    if objective.lower() in {"exit", "quit"}:
        break

    messages = [
        {
            "role": "system",
            "content": SYSTEM,
        },
        {
            "role": "user",
            "content": f"""
OBJECTIVE:
{objective}

CURRENT GIT STATUS:
{git_status()}

REPOSITORY MAP:
{repo_map()}

Begin by inspecting the relevant source code.
""".strip(),
        },
    ]

    print()

    for step in range(1, MAX_STEPS + 1):
        print(f"◉ STEP {step}/{MAX_STEPS} // computing")

        raw = ask(messages)

        try:
            action = parse_json(raw)
        except Exception as exc:
            print("↳ protocol repair:", exc)

            messages.append({
                "role": "assistant",
                "content": raw,
            })

            messages.append({
                "role": "user",
                "content":
                    'Invalid response. Return ONE valid JSON object only. '
                    'Choose read, replace, write, shell, or finish.',
            })
            continue

        kind = action.get("action", "")

        if kind == "read":
            rel = action.get("path", "")
            path = safe_path(rel)

            if path is None or not path.exists() or not path.is_file():
                observation = f"READ FAILED: {rel}"
            else:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                observation = (
                    f"FILE {rel}:\n"
                    + content[:18000]
                )

            print("↳ read", rel)

        elif kind == "replace":
            rel = action.get("path", "")
            find = action.get("find", "")
            replace = action.get("replace", "")

            path = safe_path(rel)

            if path is None or not path.exists():
                observation = f"REPLACE FAILED: invalid path {rel}"

            else:
                current = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                matches = current.count(find)

                if not find:
                    observation = "REPLACE FAILED: empty find text"

                elif matches != 1:
                    observation = (
                        f"REPLACE FAILED: expected exactly 1 match, "
                        f"found {matches} in {rel}"
                    )

                else:
                    backup(path)

                    path.write_text(
                        current.replace(find, replace, 1),
                        encoding="utf-8",
                    )

                    observation = f"REPLACE SUCCESS: {rel}"
                    print("✓ edited", rel)

        elif kind == "write":
            rel = action.get("path", "")
            content = action.get("content", "")

            path = safe_path(rel)

            if path is None:
                observation = f"WRITE FAILED: unsafe path {rel}"

            else:
                backup(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

                observation = f"WRITE SUCCESS: {rel}"
                print("✓ wrote", rel)

        elif kind == "shell":
            command = action.get("command", "")

            print("$", command)

            result = run_shell(command)

            print(result["stdout"], end="")

            if result["stderr"]:
                print(result["stderr"], end="")

            observation = json.dumps(result)

        elif kind == "finish":
            verify = action.get("verify", "").strip()

            if not verify:
                observation = (
                    "FINISH REJECTED: verification command required"
                )

            else:
                print("$", verify)

                result = run_shell(verify)

                print(result["stdout"], end="")

                if result["stderr"]:
                    print(result["stderr"], end="")

                if result["exit"] == 0:
                    print()
                    print("==============================================")
                    print("✓ GPT-DOUG VERIFIED COMPLETE")
                    print(action.get("summary", "Completed."))
                    print("==============================================")
                    print()
                    break

                observation = (
                    "FINISH REJECTED: verification failed\n"
                    + json.dumps(result)
                )

        else:
            observation = (
                "INVALID ACTION. Use read, replace, write, shell, or finish."
            )

        messages.append({
            "role": "assistant",
            "content": json.dumps(action),
        })

        messages.append({
            "role": "user",
            "content": f"""
OBSERVATION:
{observation}

CURRENT GIT STATUS:
{git_status()}

Continue the original objective.
If something failed, repair it.
Do not finish without successful verification.
""".strip(),
        })

    else:
        print()
        print("Maximum agent steps reached.")
        print("Review current git diff before continuing.")
        print()

