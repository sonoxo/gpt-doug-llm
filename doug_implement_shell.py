#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from agents import llm_backend


ROOT = Path(__file__).resolve().parent
MODEL = os.getenv("GPT_DOUG_AGENT_MODEL", llm_backend.DEFAULT_MODEL)
MAX_STEPS = int(os.getenv("GPT_DOUG_IMPLEMENT_STEPS", "50"))

BLOCKED = (
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "diskutil erase",
    "dd if=",
    "shutdown",
    "reboot",
    ":(){",
)

SECRET_MARKERS = (
    ".env",
    "credentials.json",
    "secrets.json",
    ".ssh/",
    "id_rsa",
    "id_ed25519",
)

INSPECTION_PREFIXES = (
    "pwd",
    "ls",
    "find ",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "rg ",
    "grep ",
    "head ",
    "tail ",
    "sed -n ",
)

SYSTEM = f"""
You are GPT-Doug Implement AI.

You are a persistent LOCAL software-engineering agent running inside:

{ROOT}

The human talks to you in normal language.

Their sentence IS the implementation specification.

Examples:

"implement project autosave"
"make the dashboard look premium"
"fix live preview"
"add a new coding agent"
"improve Heat Seek"
"connect project files to preview"
"repair every failing test"

EXECUTION LOOP:

understand
→ inspect relevant code
→ implement
→ run targeted tests
→ read failures
→ repair
→ verify
→ finish

YOU CONTROL THE TERMINAL.

Return exactly ONE JSON object on every turn.

ACTION 1 — shell

{{
  "action": "shell",
  "command": "command to execute"
}}

ACTION 2 — finish

{{
  "action": "finish",
  "summary": "what was actually implemented",
  "verify_command": "real command proving the implementation works"
}}

RULES:

- Natural language from the human is the specification.
- Make real source-code changes for implementation requests.
- Do not merely explain how to implement something.
- Inspect unfamiliar code before modifying it.
- Do not spend more than 3 consecutive actions browsing.
- After inspection, implement or run a targeted test.
- Do not repeatedly list the repository.
- Preserve unrelated existing work.
- Never erase user work merely to make tests pass.
- Read stdout and stderr literally.
- Automatically repair failures.
- Never repeat an identical failed command.
- Run tests/build checks appropriate to the changed code.
- A successful command is not proof that the product works.
- finish requires a real verification command.
- Never claim success after failed verification.
- Stay inside the GPT-Doug project.
- Never access credentials or unrelated private files.
- Never use Ollama.
- Never use port 11434.
- Do not output markdown.
- Do not output text outside the JSON object.
""".strip()


def run(command: str, timeout: int = 300):
    low = command.lower()

    for bad in BLOCKED:
        if bad in low:
            return 126, "", f"BLOCKED unsafe command: {bad}"

    for secret in SECRET_MARKERS:
        if secret.lower() in low:
            return 126, "", f"BLOCKED credential/private path: {secret}"

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(ROOT),
            executable="/bin/zsh",
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return (
            proc.returncode,
            proc.stdout[-14000:],
            proc.stderr[-14000:],
        )

    except subprocess.TimeoutExpired:
        return 124, "", f"Command timed out after {timeout}s"


def is_inspection(command: str) -> bool:
    value = command.strip()

    return any(
        value.startswith(prefix)
        for prefix in INSPECTION_PREFIXES
    )


def parse_action(text: str):
    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    start = text.find("{")

    if start < 0:
        raise ValueError("No JSON object")

    depth = 0
    string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if escape:
            escape = False
            continue

        if string and char == "\\":
            escape = True
            continue

        if char == '"':
            string = not string
            continue

        if string:
            continue

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return json.loads(
                    text[start:index + 1]
                )

    raise ValueError("Incomplete JSON")


def ask(messages):
    result = llm_backend.chat_once(
        messages,
        MODEL,
        {
            "temperature": 0,
            "max_tokens": 1400,
            "num_predict": 1400,
        },
    )

    return result["message"]["content"].strip()


def git_status():
    code, stdout, stderr = run(
        "git status --short",
        timeout=30,
    )

    return stdout or stderr or "(clean)"


def workspace_snapshot():
    _, output, _ = run(
        """
printf '%s\n' '--- GIT ---'
git status --short
printf '%s\n' '--- FILES ---'
find . -maxdepth 2 -type f \
  -not -path './.git/*' \
  -not -path './.venv-mlx/*' \
  -not -path './node_modules/*' \
  | sort | head -160
""",
        timeout=30,
    )

    return output


def checkpoint():
    stamp = time.strftime("%Y%m%d-%H%M%S")

    directory = (
        ROOT
        / ".doug"
        / "implement-checkpoints"
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    patch = directory / f"{stamp}.patch"
    status = directory / f"{stamp}.status"

    _, diff, _ = run(
        "git diff --binary",
        timeout=30,
    )

    patch.write_text(
        diff,
        encoding="utf-8",
    )

    status.write_text(
        git_status(),
        encoding="utf-8",
    )

    return patch


def run_objective(objective: str):
    checkpoint_path = checkpoint()

    initial = f"""
IMPLEMENT COMMAND:

{objective}

CURRENT WORKSPACE:

{workspace_snapshot()}

A recovery checkpoint was created at:

{checkpoint_path.relative_to(ROOT)}

Begin with the smallest relevant inspection necessary.
Then implement the requested behavior.
""".strip()

    messages = [
        {
            "role": "system",
            "content": SYSTEM,
        },
        {
            "role": "user",
            "content": initial,
        },
    ]

    last_command = None
    last_exit = None

    inspection_streak = 0
    successful_inspections = set()

    for step in range(1, MAX_STEPS + 1):

        print()
        print(
            f"◉ IMPLEMENT {step}/{MAX_STEPS}"
        )

        raw = ask(messages)

        try:
            action = parse_action(raw)

        except Exception as exc:

            print(
                f"↳ protocol repair: {exc}"
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": raw,
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content":
                        "Return exactly one valid JSON object. "
                        "Use shell or finish.",
                }
            )

            continue

        kind = action.get("action")

        if kind == "finish":

            verify = (
                action
                .get("verify_command", "")
                .strip()
            )

            if not verify:

                print(
                    "⚠ finish rejected: verification required"
                )

                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(action),
                    }
                )

                messages.append(
                    {
                        "role": "user",
                        "content":
                            "You cannot finish without a real "
                            "verification command.",
                    }
                )

                continue

            print()
            print("VERIFY")
            print(f"$ {verify}")

            code, stdout, stderr = run(
                verify
            )

            if stdout:
                print(stdout.rstrip())

            if stderr:
                print(stderr.rstrip())

            if code != 0:

                print(
                    f"✗ verification failed ({code})"
                )

                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(action),
                    }
                )

                messages.append(
                    {
                        "role": "user",
                        "content":
                            "VERIFICATION FAILED:\n"
                            + json.dumps(
                                {
                                    "exit": code,
                                    "stdout": stdout,
                                    "stderr": stderr,
                                }
                            )
                            + "\nRepair it and verify again.",
                    }
                )

                continue

            print()
            print(
                "✓ IMPLEMENTATION VERIFIED"
            )

            print(
                action.get(
                    "summary",
                    "Completed.",
                )
            )

            return True

        if kind != "shell":

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(action),
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content":
                        "Unknown action. "
                        "Use shell or finish.",
                }
            )

            continue

        command = (
            action
            .get("command", "")
            .strip()
        )

        if not command:
            continue

        inspection = is_inspection(command)

        if (
            command == last_command
            and last_exit not in (None, 0)
        ):

            print(
                "⛔ identical failed command blocked"
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(action),
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content":
                        "That identical command already failed. "
                        "Diagnose the failure and use a different approach.",
                }
            )

            continue

        if (
            inspection
            and command in successful_inspections
        ):

            print(
                "⛔ repeated inspection blocked"
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(action),
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content":
                        "That inspection already succeeded. "
                        "Implement code or run a targeted test now.",
                }
            )

            continue

        if (
            inspection
            and inspection_streak >= 3
        ):

            print(
                "⛔ browsing limit reached"
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(action),
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content":
                        "Enough inspection. "
                        "Your next action must modify implementation "
                        "or run a targeted test.",
                }
            )

            continue

        print(f"$ {command}")

        code, stdout, stderr = run(
            command
        )

        if stdout:
            print(stdout.rstrip())

        if stderr:
            print(stderr.rstrip())

        print(
            f"↳ exit={code}"
        )

        last_command = command
        last_exit = code

        if code == 0 and inspection:
            successful_inspections.add(command)
            inspection_streak += 1

        elif not inspection:
            inspection_streak = 0

        observation = {
            "command": command,
            "exit": code,
            "stdout": stdout,
            "stderr": stderr,
            "git_status": git_status(),
        }

        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(action),
            }
        )

        messages.append(
            {
                "role": "user",
                "content":
                    "TERMINAL RESULT:\n"
                    + json.dumps(observation)
                    + "\nContinue implementing the original command. "
                      "Repair failures automatically.",
            }
        )

    print()
    print(
        "⚠ step budget reached; command not verified complete"
    )

    return False


def self_test():
    assert parse_action(
        '{"action":"shell","command":"pwd"}'
    )["action"] == "shell"

    assert is_inspection(
        "git status --short"
    )

    assert not is_inspection(
        "python -m pytest -q"
    )

    print("doug-implement self-test passed")


def help_text():
    print(
        """
COMMANDS

/help       show commands
/status     git status
/diff       git diff --stat
/test       run pytest
/health     Qwen provider health
/clear      clear terminal
/quit       exit

EVERYTHING ELSE IS AN IMPLEMENTATION COMMAND.

Examples:

implement> add autosave to projects

implement> fix live preview

implement> make the UI look like a premium AI builder

implement> add an agent manager with start stop and status controls

implement> inspect the failing tests and repair all of them

implement> upgrade Heat Seek without breaking existing functionality
"""
    )


def main():

    if "--self-test" in sys.argv:
        self_test()
        return

    print()
    print(
        "╔══════════════════════════════════════════════╗"
    )
    print(
        "║        GPT-DOUG IMPLEMENT AI                ║"
    )
    print(
        "║       QWEN CODER • MLX • LOCAL              ║"
    )
    print(
        "╚══════════════════════════════════════════════╝"
    )
    print()

    print(
        f"MODEL     : {MODEL}"
    )

    print(
        f"WORKSPACE : {ROOT}"
    )

    print(
        "OLLAMA    : OFF"
    )

    print()
    print(
        "Type implementation commands in normal language."
    )

    print(
        "Type /help for controls."
    )

    while True:

        try:
            command = input(
                "\nimplement> "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError,
        ):
            print()
            break

        if not command:
            continue

        if command in {
            "/quit",
            "/exit",
            "quit",
            "exit",
        }:
            break

        if command == "/help":
            help_text()
            continue

        if command == "/status":
            print(
                git_status()
            )
            continue

        if command == "/diff":
            _, stdout, stderr = run(
                "git diff --stat && git diff --check"
            )

            print(
                stdout or stderr
            )

            continue

        if command == "/test":
            code, stdout, stderr = run(
                "python -m pytest -q"
            )

            print(
                stdout or stderr
            )

            print(
                f"exit={code}"
            )

            continue

        if command == "/health":
            print(
                json.dumps(
                    llm_backend.health(),
                    indent=2,
                )
            )

            continue

        if command == "/clear":
            os.system("clear")
            continue

        run_objective(command)


if __name__ == "__main__":
    main()
