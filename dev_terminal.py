"""Constrained EUREKA 369 developer diagnostics terminal."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from auth_gate import ThreeFactorGate
from compliance import UserContext


class DevTerminal:
    """Allowlisted diagnostics only; never evaluates commands or opens a shell."""

    ALLOWED_ROLES = {"developer", "admin"}
    CONFIG_KEYS = (
        "GPT_DOUG_JURISDICTION", "GPT_DOUG_ORG_TYPE", "GPT_DOUG_ROLE",
        "GPT_DOUG_AGE_VERIFIED", "GPT_DOUG_GOV_AUTHORIZED",
        "GPT_DOUG_HUMAN_OVERSIGHT", "FOUNDRY_ALLOWED_HOST",
    )

    def __init__(self, auth: ThreeFactorGate, context: UserContext, project_root: str | Path, audit_path: str | Path):
        self.auth = auth
        self.context = context
        self.project_root = Path(project_root).resolve()
        self.audit_path = Path(audit_path)

    def elevate(self, fresh_totp: str) -> bool:
        return self.context.role in self.ALLOWED_ROLES and self.auth.authenticate(fresh_totp)

    def execute(self, command: str) -> str:
        command = command.strip().lower()
        if command == "help":
            return "help | status | audit | config | exit"
        if command == "status":
            return f"EUREKA 369 ACTIVE // role={self.context.role} // root={self.project_root.name}"
        if command == "audit":
            if not self.audit_path.exists():
                return "No Zyra audit events."
            lines = self.audit_path.read_text(encoding="utf-8").splitlines()[-10:]
            safe = []
            for line in lines:
                try:
                    event = json.loads(line)
                    safe.append(json.dumps({key: event.get(key) for key in ("timestamp", "direction", "allowed", "risk", "reasons")}))
                except json.JSONDecodeError:
                    continue
            return "\n".join(safe) or "No valid Zyra audit events."
        if command == "config":
            return "\n".join(f"{key}={os.getenv(key, '<unset>')}" for key in self.CONFIG_KEYS)
        if command == "exit":
            return "EXIT"
        return "DENIED // command is not allowlisted. Type help."

    def run(self, input_fn=input, output_fn=print, session_seconds: int = 300, max_commands: int = 20) -> None:
        output_fn("ASTRAL // EUREKA 369 // TWO-PERSON DEV TERMINAL // NO SHELL ACCESS")
        deadline = time.monotonic() + min(session_seconds, 300)
        commands = 0
        while True:
            if time.monotonic() >= deadline or commands >= min(max_commands, 20):
                output_fn("ASTRAL SESSION EXPIRED // re-authentication required")
                return
            try:
                command = input_fn("e369 > ")
            except (EOFError, KeyboardInterrupt):
                output_fn("Developer session closed.")
                return
            result = self.execute(command)
            commands += 1
            if result == "EXIT":
                output_fn("Developer session closed.")
                return
            output_fn(result)
