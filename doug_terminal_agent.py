#!/usr/bin/env python3

import json
import os
import subprocess
import sys
from pathlib import Path

from agents import llm_backend

MODEL = os.getenv("GPT_DOUG_AGENT_MODEL", llm_backend.DEFAULT_MODEL)
MAX_STEPS = int(os.getenv("GPT_DOUG_MAX_STEPS", "60"))

workspace = Path.cwd().resolve()

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
{{"action":"finish","summary":"what was actually completed and verified"}}

RULES:
- Return exactly ONE JSON object.
- Never wrap JSON in markdown.
- Never pretend a command ran.
- Inspect before changing unfamiliar projects.
- Spend no more than 3 consecutive steps only inspecting files.
- After initial inspection, make a concrete code change or run a targeted test.
- Do not repeatedly run ls, find, pwd, git status, git diff, grep, rg, head, tail, or sed without making progress.
- A successful inspection command is not implementation progress.
- For build/fix/upgrade/add requests, make actual source changes whenever technically possible.
- Prefer targeted edits over repeatedly surveying the entire repository.
- Use relative paths inside the workspace whenever possible.
- Preserve existing files unless modification is necessary.
- Read command output before choosing the next action.
- If something fails, diagnose it and try a corrected approach.
- NEVER repeat an identical command that just failed.
- Read stderr literally.
- If a path says 'No such file or directory', inspect/create its parent directories.
- mkdir -p must include every required nested directory.
- Run tests/build checks when available.
- Never use finish after a failed command.
- Before finish, repair every failure.
- finish MUST include verify_command.
- verify_command must actually test the requested result.
- Examples: test files exist, run tests, curl the server, compile the code.
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
)

def ask(messages):
    result = llm_backend.chat_once(messages, MODEL, {
        "temperature": 0,
        "num_ctx": 4096,
        "format": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["shell", "finish"]},
                "command": {"type": "string"},
                "summary": {"type": "string"},
                "verify_command": {"type": "string"}
            },
            "required": ["action"]
        }
    })
    return result["message"]["content"].strip()

def parse_action(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    return json.loads(text)

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
        timeout=300,
        executable="/bin/zsh",
    )

    return proc.returncode, proc.stdout[-12000:], proc.stderr[-12000:]


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
    "sed -n ",
    "head ",
    "tail ",
)

def is_inspection_command(command):
    value = command.strip()
    return any(value.startswith(prefix) for prefix in INSPECTION_PREFIXES)

def main():
    if len(sys.argv) < 2:
        print('Usage: doug-agent "build a web app"')
        raise SystemExit(1)

    objective = " ".join(sys.argv[1:])

    _, snapshot_out, snapshot_err = run(
        "git status --short; "
        "printf '\\n--- PROJECT FILES ---\\n'; "
        "find . -maxdepth 2 -type f "
        "-not -path './.git/*' "
        "-not -path './.venv-mlx/*' "
        "-not -path './node_modules/*' "
        "| sort | head -140"
    )

    initial_context = (
        objective
        + "\n\nINITIAL WORKSPACE SNAPSHOT:\n"
        + snapshot_out
        + "\n"
        + snapshot_err
        + "\n\nChoose the relevant implementation surface immediately. "
          "Do not spend more than three steps browsing before editing or testing."
    )

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": initial_context},
    ]

    print()
    print("╔══════════════════════════════════════╗")
    print("║ GPT6-DOUG TERMINAL AGENT // ONLINE   ║")
    print("╚══════════════════════════════════════╝")
    print(f"MODEL     : {MODEL}")
    print(f"WORKSPACE : {workspace}")
    print(f"OBJECTIVE : {objective}")
    print()

    last_command = None
    last_exit_code = None
    repeat_failures = 0
    successful_inspections = set()
    inspection_streak = 0

    for step in range(1, MAX_STEPS + 1):

        print(f"◉ STEP {step}/{MAX_STEPS} // THINKING")

        raw = ask(messages)

        try:
            action = parse_action(raw)
        except Exception:
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content":
                'Invalid protocol. Return ONLY JSON like '
                '{"action":"shell","command":"pwd"} or '
                '{"action":"finish","summary":"verified result"}'
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
                code, stdout, stderr = 124, "", "Verification timed out."

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
            continue

        # ANTI-LOOP: never execute the exact same failed command repeatedly.
        if command == last_command and last_exit_code not in (None, 0):
            repeat_failures += 1
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

        inspection = is_inspection_command(command)

        if inspection and command in successful_inspections:
            print()
            print("⛔ INSPECTION LOOP BLOCKED")
            print(f"│ Already completed successfully: {command}")
            print("│ Make a code change or run a targeted verification command.")
            print()

            messages.append({
                "role": "assistant",
                "content": json.dumps(action)
            })

            messages.append({
                "role": "user",
                "content":
                    "PROGRESS_GUARD: This inspection already succeeded. "
                    "Do not repeat repository browsing. "
                    "Make a concrete source-code modification or run a targeted test now."
            })

            continue

        if inspection and inspection_streak >= 3:
            print()
            print("⛔ INSPECTION LIMIT REACHED")
            print("│ Three consecutive browsing steps completed.")
            print("│ Implementation or targeted testing is now required.")
            print()

            messages.append({
                "role": "assistant",
                "content": json.dumps(action)
            })

            messages.append({
                "role": "user",
                "content":
                    "PROGRESS_GUARD: You have completed enough inspection. "
                    "Your next action must implement the requested feature, "
                    "repair code, or run a targeted test. "
                    "Do not list or search the repository again."
            })

            continue

        print()
        print("┌─ GPT6-DOUG → TERMINAL")
        print(f"│ $ {command}")
        print("└────────────────────────────────────")

        try:
            code, stdout, stderr = run(command)
        except subprocess.TimeoutExpired:
            code, stdout, stderr = 124, "", "Command timed out after 300 seconds."

        if stdout:
            print(stdout.rstrip())

        if stderr:
            print(stderr.rstrip())

        print(f"↳ exit={code}")
        print()

        last_command = command
        last_exit_code = code
        if code == 0:
            repeat_failures = 0

            if inspection:
                successful_inspections.add(command)
                inspection_streak += 1
            else:
                inspection_streak = 0
        else:
            if not inspection:
                inspection_streak = 0

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
