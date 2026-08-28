#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from agents import llm_backend, qwen_gateway

PROVIDER = os.getenv("GPT_DOUG_PROVIDER", "").strip().lower()
MODEL = os.getenv("GPT_DOUG_AGENT_MODEL", "").strip() or (
    qwen_gateway.DEFAULT_MODEL if PROVIDER == "qwen" else llm_backend.DEFAULT_MODEL
)
MAX_STEPS = max(4, int(os.getenv("GPT_DOUG_AGENT_MAX_STEPS", "40")))
MAX_CONTEXT_CHARS = max(12000, int(os.getenv("GPT_DOUG_AGENT_CONTEXT_CHARS", "48000")))
COMMAND_TIMEOUT = max(30, int(os.getenv("GPT_DOUG_AGENT_COMMAND_TIMEOUT", "300")))

workspace = Path.cwd().resolve()
state_dir = workspace / ".doug"
state_dir.mkdir(parents=True, exist_ok=True)
VERIFICATION_LOG = state_dir / "terminal-verification.jsonl"

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["shell", "finish"]},
        "command": {"type": "string"},
        "summary": {"type": "string"},
        "verify_command": {"type": "string"},
    },
    "required": ["action"],
    "additionalProperties": False,
}

SYSTEM = f"""
You are GPT-Doug Terminal Agent, a verification-first software-engineering agent.

You control a terminal through a structured action protocol.

WORKSPACE:
{workspace}

OBJECTIVE:
Complete the user's requested software-engineering task.

OPERATING LOOP:
inspect -> decide -> execute -> observe -> repair -> test -> verify

LONG-HORIZON EXECUTION:
- Maintain progress across many steps without repeating failed work.
- Prefer small, inspectable changes over speculative rewrites.
- Re-read the latest terminal evidence before every repair decision.
- When context becomes long, preserve the objective, current failure, changed files, and verification evidence.
- Treat successful command execution as evidence, not proof of task completion.

ACTIONS:
1. shell
{{"action":"shell","command":"pwd && ls"}}

2. finish
{{"action":"finish","summary":"what was actually completed","verify_command":"real command proving the requested result"}}

RULES:
- Return exactly ONE JSON object.
- Never wrap JSON in markdown.
- Never pretend a command ran.
- Inspect before changing unfamiliar projects.
- Use relative paths inside the workspace whenever possible.
- Preserve existing files unless modification is necessary.
- Read command output before choosing the next action.
- If something fails, diagnose it and use a corrected approach.
- NEVER repeat a command that already failed during this run unless new evidence makes it materially different.
- Read stderr literally.
- If a path says 'No such file or directory', inspect/create its parent directories.
- mkdir -p must include every required nested directory.
- Run tests/build checks when available.
- Never use finish after an unresolved failed command.
- Before finish, repair every relevant failure.
- finish MUST include verify_command.
- verify_command must actually test the requested result.
- A claim is not verification.
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
    "sudo rm -rf",
)


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


def command_fingerprint(command: str) -> str:
    normalized = normalize_command(command)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compact_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    total = sum(len(item.get("content", "")) for item in messages)
    if total <= MAX_CONTEXT_CHARS or len(messages) <= 4:
        return messages

    head = messages[:2]
    tail: list[dict[str, str]] = []
    budget = MAX_CONTEXT_CHARS - sum(len(item.get("content", "")) for item in head) - 1200

    for item in reversed(messages[2:]):
        content = item.get("content", "")
        if tail and budget - len(content) < 0:
            break
        tail.append(item)
        budget -= len(content)

    tail.reverse()
    marker = {
        "role": "user",
        "content": (
            "CONTEXT COMPACTED: Earlier terminal turns were removed to preserve execution quality. "
            "The original objective and the most recent evidence remain authoritative."
        ),
    }
    return head + [marker] + tail


def ask(messages: list[dict[str, str]]) -> str:
    prepared = compact_messages(messages)
    options = {
        "temperature": 0,
        "num_ctx": 16384,
        "max_tokens": 4096,
        "format": ACTION_SCHEMA,
    }
    if PROVIDER == "qwen":
        result = qwen_gateway.chat_once(prepared, MODEL, options)
    else:
        result = llm_backend.chat_once(prepared, MODEL, options)
    return result["message"]["content"].strip()


def parse_action(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    action = json.loads(text)
    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object")
    return action


def unsafe_reason(command: str) -> str | None:
    low = normalize_command(command).lower()
    for bad in BLOCKED:
        if bad in low:
            return bad
    return None


def run(command: str) -> tuple[int, str, str]:
    bad = unsafe_reason(command)
    if bad:
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

    return proc.returncode, proc.stdout[-12000:], proc.stderr[-12000:]


def record_verification(*, objective: str, command: str, code: int, stdout: str, stderr: str) -> None:
    entry = {
        "timestamp": int(time.time()),
        "objective": objective,
        "provider": PROVIDER or "default",
        "model": MODEL,
        "workspace": str(workspace),
        "verify_command": command,
        "exit_code": code,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
    }
    with VERIFICATION_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def append_observation(
    messages: list[dict[str, str]],
    *,
    action: dict,
    command: str,
    code: int,
    stdout: str,
    stderr: str,
) -> None:
    messages.append({"role": "assistant", "content": json.dumps(action)})
    messages.append(
        {
            "role": "user",
            "content": (
                "TERMINAL OBSERVATION:\n"
                + json.dumps(
                    {
                        "command": command,
                        "exit_code": code,
                        "stdout": stdout,
                        "stderr": stderr,
                    }
                )
                + "\nContinue the objective. Repair relevant failures automatically."
            ),
        }
    )


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: doug-agent "build a web app"')
        raise SystemExit(1)

    objective = " ".join(sys.argv[1:])

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": objective},
    ]

    print()
    print("╔══════════════════════════════════════╗")
    print("║ GPT-DOUG TERMINAL AGENT // ONLINE    ║")
    print("╚══════════════════════════════════════╝")
    print(f"PROVIDER  : {PROVIDER or 'default'}")
    print(f"MODEL     : {MODEL}")
    print(f"WORKSPACE : {workspace}")
    print(f"OBJECTIVE : {objective}")
    print(f"MAX STEPS : {MAX_STEPS}")
    print()

    failed_commands: set[str] = set()
    last_exit_code: int | None = None
    protocol_failures = 0

    for step in range(1, MAX_STEPS + 1):
        print(f"◉ STEP {step}/{MAX_STEPS} // THINKING")

        raw = ask(messages)

        try:
            action = parse_action(raw)
        except Exception as exc:
            protocol_failures += 1
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "INVALID PROTOCOL: Return ONLY one JSON object. "
                        "For shell use {\"action\":\"shell\",\"command\":\"pwd\"}. "
                        "For finish use {\"action\":\"finish\",\"summary\":\"verified result\","
                        "\"verify_command\":\"real verification command\"}. "
                        f"Parser error: {type(exc).__name__}."
                    ),
                }
            )
            print("  ↳ protocol correction")
            if protocol_failures >= 5:
                print("❌ Too many protocol failures; refusing to invent execution state.")
                raise SystemExit(3)
            continue

        protocol_failures = 0
        kind = action.get("action")

        if kind == "finish":
            verify = str(action.get("verify_command", "")).strip()

            if last_exit_code not in (None, 0):
                print("⚠️ FINISH REJECTED // unresolved command failure")
                messages.append({"role": "assistant", "content": json.dumps(action)})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You may not finish immediately after a failed command. "
                            "Repair or explicitly verify that the failure is irrelevant to the objective."
                        ),
                    }
                )
                continue

            if not verify:
                print("⚠️ FINISH REJECTED // no verification command")
                messages.append({"role": "assistant", "content": json.dumps(action)})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You may not finish yet. Supply a real shell verification command "
                            "that proves the requested result."
                        ),
                    }
                )
                continue

            print()
            print("┌─ GPT-DOUG → VERIFY")
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

            record_verification(
                objective=objective,
                command=verify,
                code=code,
                stdout=stdout,
                stderr=stderr,
            )

            if code != 0:
                print("❌ VERIFICATION FAILED // continuing repair loop")
                failed_commands.add(command_fingerprint(verify))
                append_observation(
                    messages,
                    action=action,
                    command=verify,
                    code=code,
                    stdout=stdout,
                    stderr=stderr,
                )
                last_exit_code = code
                continue

            print()
            print("✅ GPT-DOUG VERIFIED COMPLETE")
            print(action.get("summary", "Completed and verified."))
            print(f"EVIDENCE  : {VERIFICATION_LOG}")
            return

        if kind != "shell":
            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append({"role": "user", "content": "Unknown action. Use shell or finish."})
            continue

        command = str(action.get("command", "")).strip()
        if not command:
            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append({"role": "user", "content": "Shell action requires a non-empty command."})
            continue

        fingerprint = command_fingerprint(command)
        if fingerprint in failed_commands:
            print()
            print("⛔ REPEAT BLOCKED // this command already failed during this run")
            print(f"│ $ {command}")
            print("│ Diagnose the evidence and issue a materially different command.")
            print()
            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "REPEAT_BLOCKED: This command already failed earlier in the run. "
                        "Do not repeat it. Inspect the recorded stderr/stdout and choose a different repair."
                    ),
                }
            )
            continue

        print()
        print("┌─ GPT-DOUG → TERMINAL")
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

        last_exit_code = code
        if code != 0:
            failed_commands.add(fingerprint)

        append_observation(
            messages,
            action=action,
            command=command,
            code=code,
            stdout=stdout,
            stderr=stderr,
        )

    print("⚠️ Maximum agent steps reached without verified completion.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
