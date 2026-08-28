#!/usr/bin/env python3

import json
import os
import subprocess
import sys
from pathlib import Path

from agents import llm_backend

MODEL = os.getenv("GPT_DOUG_AGENT_MODEL", llm_backend.DEFAULT_MODEL)
MAX_STEPS = max(1, int(os.getenv("GPT_DOUG_AGENT_MAX_STEPS", "40")))
CONTEXT_WINDOW = max(4096, int(os.getenv("GPT_DOUG_AGENT_CONTEXT", "262144")))
COMMAND_TIMEOUT = max(10, int(os.getenv("GPT_DOUG_AGENT_COMMAND_TIMEOUT", "300")))
OUTPUT_LIMIT = max(4000, int(os.getenv("GPT_DOUG_AGENT_OUTPUT_LIMIT", "20000")))

workspace = Path.cwd().resolve()

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["shell", "finish"]},
        "command": {"type": "string"},
        "summary": {"type": "string"},
        "verify_command": {"type": "string"},
    },
    "required": ["action"],
}

SYSTEM = f"""
You are GPT6-Doug Terminal Agent.

You control a terminal through a structured action protocol.

WORKSPACE:
{workspace}

OBJECTIVE:
Complete the user's requested software-engineering task.

LOOP:
inspect -> decide -> execute -> observe -> repair -> test -> verify

You have exactly these actions:

1. shell
{{"action":"shell","command":"pwd && ls"}}

2. finish
{{"action":"finish","summary":"what was actually completed and verified","verify_command":"real verification command"}}

RULES:
- Return exactly ONE JSON object.
- Never wrap JSON in markdown.
- Never pretend a command ran.
- Inspect before changing unfamiliar projects.
- Use relative paths inside the workspace whenever possible.
- Preserve existing files unless modification is necessary.
- Read command output before choosing the next action.
- If something fails, diagnose it and try a corrected approach.
- NEVER repeat an identical command that just failed.
- Read stderr literally.
- If a path says 'No such file or directory', inspect/create its parent directories.
- mkdir -p must include every required nested directory.
- Run tests/build checks when available.
- Prefer targeted tests during iteration, then a broader regression check before finish.
- Never use finish after a failed command.
- Before finish, repair every failure.
- finish MUST include verify_command.
- verify_command must actually test the requested result.
- Examples: test files exist, run tests, curl the server, compile the code.
- A claim is not verification.
- Keep observations evidence-dense; do not waste context restating unchanged facts.
- For long tasks, periodically inspect git diff/status so the plan stays grounded in actual changes.
- Do not execute destructive disk/system commands.
- Do not access credentials or unrelated private files.
"""

BLOCKED = (
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "diskutil erase",
    "dd if=",
    ":(){",
    "shutdown",
    "reboot",
)


def ask(messages):
    result = llm_backend.chat_once(messages, MODEL, {
        "temperature": 0,
        "num_ctx": CONTEXT_WINDOW,
        "format": ACTION_SCHEMA,
    })
    if result.get("error"):
        raise RuntimeError(f"LLM provider error: {result['error']}")
    message = result.get("message") or {}
    content = message.get("content", "")
    if not content:
        raise RuntimeError("LLM provider returned an empty response")
    return content.strip()


def parse_action(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    action = json.loads(text)
    if not isinstance(action, dict):
        raise ValueError("agent action must be a JSON object")
    return action


def run(command):
    low = command.lower()

    for bad in BLOCKED:
        if bad in low:
            return 126, "", f"BLOCKED unsafe command: {bad}"

    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(workspace),
        text=True,
        capture_output=True,
        timeout=COMMAND_TIMEOUT,
        executable="/bin/zsh",
    )

    return proc.returncode, proc.stdout[-OUTPUT_LIMIT:], proc.stderr[-OUTPUT_LIMIT:]


def main():
    if len(sys.argv) < 2:
        print('Usage: doug-agent "build a web app"')
        raise SystemExit(1)

    objective = " ".join(sys.argv[1:])

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": objective},
    ]

    print()
    print("╔══════════════════════════════════════╗")
    print("║ GPT6-DOUG TERMINAL AGENT // ONLINE   ║")
    print("╚══════════════════════════════════════╝")
    print(f"MODEL     : {MODEL}")
    print(f"CONTEXT   : {CONTEXT_WINDOW:,} tokens")
    print(f"MAX STEPS : {MAX_STEPS}")
    print(f"WORKSPACE : {workspace}")
    print(f"OBJECTIVE : {objective}")
    print()

    last_command = None
    last_exit_code = None

    for step in range(1, MAX_STEPS + 1):
        print(f"◉ STEP {step}/{MAX_STEPS} // THINKING")

        try:
            raw = ask(messages)
        except Exception as exc:
            print(f"❌ MODEL CALL FAILED // {exc}")
            raise SystemExit(3) from exc

        try:
            action = parse_action(raw)
        except Exception:
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content":
                'Invalid protocol. Return ONLY JSON like '
                '{"action":"shell","command":"pwd"} or '
                '{"action":"finish","summary":"verified result","verify_command":"pytest -q"}'
            })
            print("  ↳ protocol correction")
            continue

        kind = action.get("action")

        if kind == "finish":
            verify = action.get("verify_command", "").strip()

            if not verify:
                print("⚠️ FINISH REJECTED // no verification command")
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": "You may not finish yet. Supply a real shell verification command and fix any remaining failures."
                })
                continue

            print()
            print("┌─ GPT6-DOUG → VERIFY")
            print(f"│ $ {verify}")
            print("└────────────────────────────────────")

            try:
                code, stdout, stderr = run(verify)
            except subprocess.TimeoutExpired:
                code, stdout, stderr = 124, "", f"Verification timed out after {COMMAND_TIMEOUT} seconds."

            if stdout:
                print(stdout.rstrip())
            if stderr:
                print(stderr.rstrip())

            print(f"↳ verify exit={code}")

            if code != 0:
                print("❌ VERIFICATION FAILED // continuing repair loop")
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": "VERIFICATION FAILED:\n" +
                               json.dumps({
                                   "command": verify,
                                   "exit_code": code,
                                   "stdout": stdout,
                                   "stderr": stderr
                               }) +
                               "\nRepair the problem and test again. Do not finish."
                })
                continue

            print()
            print("✅ GPT6-DOUG VERIFIED COMPLETE")
            print(action.get("summary", "Completed and verified."))
            return

        if kind != "shell":
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": "Unknown action. Use shell or finish."
            })
            continue

        command = action.get("command", "").strip()

        if not command:
            messages.append({
                "role": "user",
                "content": "A shell action requires a non-empty command."
            })
            continue

        if command == last_command and last_exit_code not in (None, 0):
            print()
            print("⛔ REPEAT BLOCKED // previous identical command already failed")
            print(f"│ $ {command}")
            print("│ Change the approach. Inspect the error and issue a DIFFERENT command.")
            print()

            messages.append({
                "role": "assistant",
                "content": json.dumps(action)
            })
            messages.append({
                "role": "user",
                "content":
                    "REPEAT_BLOCKED: That exact command already failed. "
                    "DO NOT repeat it. Diagnose the stderr. "
                    "Inspect the filesystem if necessary and issue a DIFFERENT corrected command. "
                    "For missing nested directories, create all required parent directories first."
            })
            continue

        print()
        print("┌─ GPT6-DOUG → TERMINAL")
        print(f"│ $ {command}")
        print("└────────────────────────────────────")

        try:
            code, stdout, stderr = run(command)
        except subprocess.TimeoutExpired:
            code, stdout, stderr = 124, "", f"Command timed out after {COMMAND_TIMEOUT} seconds."

        if stdout:
            print(stdout.rstrip())

        if stderr:
            print(stderr.rstrip())

        print(f"↳ exit={code}")
        print()

        last_command = command
        last_exit_code = code

        observation = {
            "command": command,
            "exit_code": code,
            "stdout": stdout,
            "stderr": stderr,
        }

        messages.append({
            "role": "assistant",
            "content": json.dumps(action)
        })

        messages.append({
            "role": "user",
            "content":
                "TERMINAL OBSERVATION:\n" +
                json.dumps(observation) +
                "\nContinue the objective. Fix failures automatically."
        })

    print("⚠️ Maximum agent steps reached without verified completion.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
