"""Cooperative, latched AI emergency stop for operator-controlled GPT-Doug runtimes.

No network access, background daemon, provider credentials, process discovery,
or physical-system control. Every cooperating AI entry point checks this gate.
For adversarial processes use host-managed file permissions and network egress
controls; Python code alone cannot police unrelated AI infrastructure.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, TypeVar

DEFAULT_STATE_DIR = "~/.gpt-doug/ai-killswitch"
STATE_DIRECTORY_ENV = "GPT_DOUG_AI_STOP_DIR"
REQUIRED_STOP_DIR_ENV = "GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY"
FORCE_STOP_ENV = "GPT_DOUG_AI_BLOCK_ALL"
STOP_FILENAME = "STOP"
# Exact, non-secret human operator command; not a chat/prompt substring trigger.
ACTIVATION_PHRASE = "gpt-doug-llm stop the kraken"
_ACTIVATION_TOKENS = ("stop", "the", "kraken")
_CONFIRMATION = "REARM GPT-DOUG AI"

T = TypeVar("T")


class AIKillSwitchEngaged(PermissionError):
    """AI inference, AI-led tool use and autonomous worker execution are halted."""


def _directory() -> Path:
    raw = os.getenv(STATE_DIRECTORY_ENV, DEFAULT_STATE_DIR)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("AI stop directory must not be empty")
    candidate = Path(raw).expanduser()
    if os.environ.get(STATE_DIRECTORY_ENV) is not None and not candidate.is_absolute():
        raise ValueError("configured AI stop directory must be absolute")
    return candidate.absolute()


def _forced_stop() -> str | None:
    raw = os.environ.get(FORCE_STOP_ENV, "").strip().lower()
    if raw in ("", "0", "false", "no", "off"):
        return None
    if raw in ("1", "true", "yes", "on"):
        return "host_enforced_stop"
    return "invalid_host_stop_configuration"


def _required_stop_directory() -> bool:
    """Strict deployments must not infer RUNNING from a missing stop volume."""
    raw = os.environ.get(REQUIRED_STOP_DIR_ENV, "0").strip().lower()
    if raw in ("", "0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    raise ValueError("invalid required stop directory configuration")


def _latch_path() -> Path:
    return _directory() / STOP_FILENAME


def _check_path(path: Path) -> str | None:
    """Return a fail-closed reason if anything suspicious exists at path."""
    try:
        parent_info = path.parent.lstat()
    except FileNotFoundError:
        return None  # Switch has never been installed on this machine.
    except OSError:
        return "unreadable_stop_directory"
    if not stat.S_ISDIR(parent_info.st_mode):
        return "unsafe_stop_directory"
    try:
        file_info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        return "unreadable_stop_latch"
    if not stat.S_ISREG(file_info.st_mode):
        return "invalid_stop_latch_type"
    return "operator_stop_latched"


def status() -> dict[str, Any]:
    """Inspectable while stopped; errors in switch state fail closed."""
    reason = _forced_stop()
    try:
        required = _required_stop_directory()
    except ValueError:
        required = False
        reason = reason or "invalid_required_stop_directory_configuration"
    try:
        path = _latch_path()
        path_reason = _check_path(path)
        if path_reason and not reason:
            reason = path_reason
        if required and not path_reason:
            # Missing operator-mounted state is unsafe in strict deployments.
            try:
                parent_info = path.parent.lstat()
            except FileNotFoundError:
                reason = reason or "required_stop_directory_missing"
            except OSError:
                reason = reason or "unreadable_stop_directory"
            else:
                if not stat.S_ISDIR(parent_info.st_mode):
                    reason = reason or "unsafe_stop_directory"
        display_path = str(path)
    except (OSError, ValueError, RuntimeError):
        display_path = None
        reason = reason or "invalid_stop_configuration"
    return {
        "stopped": reason is not None,
        "reason": reason or "running",
        "stop_directory_required": required,
        "state_dir": display_path,
        "scope": "cooperating_AI_processes_on_this_host_or_shared_mount",
        "external_ai_control": False,
    }


def require_ai_allowed(operation: str = "AI execution") -> None:
    state = status()
    if state["stopped"]:
        raise AIKillSwitchEngaged(
            f"AI_KILLSWITCH_ENGAGED: {operation} denied ({state['reason']})"
        )


def guarded_stream(source: Iterable[T], operation: str = "AI streaming") -> Iterator[T]:
    """Cease delivery as soon as the cooperative caller observes STOP."""
    iterator = iter(source)
    try:
        require_ai_allowed(operation)
        for event in iterator:
            require_ai_allowed(operation)
            yield event
    finally:
        closer = getattr(iterator, "close", None)
        if callable(closer):
            closer()


def interruptible_sleep(seconds: float, operation: str = "AI retry") -> None:
    """Bounded backoff that notices a stop within about 200 milliseconds."""
    deadline = time.monotonic() + max(0.0, seconds)
    while True:
        require_ai_allowed(operation)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.2, remaining))


def _secure_directory() -> Path:
    directory = _directory()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not stat.S_ISDIR(directory.lstat().st_mode):
        raise OSError("refusing non-directory AI stop state")
    return directory


def _append_audit(directory: Path, action: str, reason: str) -> None:
    record = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "reason": reason[:160],
        "pid": os.getpid(),
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(directory / "operator-audit.jsonl"), flags, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        # Audit failure cannot undo a latched stop. Production audit should
        # additionally be sent to a tamper-resistant operator-owned sink.
        pass


def emergency_stop(reason: str = "operator_emergency_stop") -> dict[str, Any]:
    """Persistently latch STOP. This does not kill unrelated OS processes."""
    directory = _secure_directory()
    path = directory / STOP_FILENAME
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    created = False
    try:
        fd = os.open(str(path), flags, 0o600)
        created = True
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"state": "STOPPED", "reason": reason[:160]}, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        pass  # Idempotent, but still fail closed if STOP is corrupt/symlinked.
    if created:
        _append_audit(directory, "STOP", reason)
    state = status()
    if not state["stopped"]:
        raise OSError("AI stop latch could not be verified")
    return state


def _resume_after_interactive_confirmation() -> dict[str, Any]:
    if not sys.stdin.isatty():
        raise PermissionError("rearm requires an interactive human-operated terminal")
    answer = input(f"Type '{_CONFIRMATION}' to restart AI: ")
    if answer != _CONFIRMATION:
        raise PermissionError("operator rearm confirmation did not match")
    if _forced_stop() is not None:
        raise PermissionError("host-enforced AI stop must be cleared by its operator")
    if _required_stop_directory():
        # Rearming must not quietly recreate an absent or unmounted state volume.
        try:
            directory_info = _directory().lstat()
        except OSError as error:
            raise PermissionError("required operator stop directory is unavailable") from error
        if not stat.S_ISDIR(directory_info.st_mode):
            raise PermissionError("required operator stop directory is unsafe")
    directory = _secure_directory()
    path = directory / STOP_FILENAME
    if path.is_symlink():
        raise PermissionError("refusing to rearm through a symlink")
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    _append_audit(directory, "REARM", "interactive_operator_confirmed")
    state = status()
    if state["stopped"]:
        raise PermissionError("AI remains stopped")
    return state


def _normalized_cli_argv(argv: list[str] | None = None) -> list[str]:
    """Interpret only the exact operator phrase, never arbitrary prompt text."""
    received = list(sys.argv[1:] if argv is None else argv)
    lower = tuple(token.casefold() for token in received)
    if lower in (
        _ACTIVATION_TOKENS,
        ("gpt-doug-llm",) + _ACTIVATION_TOKENS,
        (ACTIVATION_PHRASE,),
    ):
        return ["stop", "--reason", "operator_stop_the_kraken"]
    return received


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operator-controlled AI execution stop")
    parser.add_argument("action", choices=("status", "stop", "resume", "check"))
    parser.add_argument("--reason", default="operator_emergency_stop")
    args = parser.parse_args(_normalized_cli_argv(argv))
    try:
        if args.action == "stop":
            state = emergency_stop(args.reason)
        elif args.action == "resume":
            state = _resume_after_interactive_confirmation()
        else:
            state = status()
        print(json.dumps(state, sort_keys=True))
        return 3 if args.action == "check" and state["stopped"] else 0
    except (OSError, PermissionError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "stopped": status()["stopped"]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
