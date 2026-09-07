from __future__ import annotations

"""Clawbot-style local computer tools for GPT-DOUG / Wakeup3lm.

The toolbox is intentionally local-first and capability-gated. Read-only
operations may run immediately; actions with meaningful side effects require an
explicit ``approve=True`` argument. Catastrophic shell patterns are rejected
rather than delegated to the model.
"""

import argparse
import importlib.util
import json
import os
import platform
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


class ComputerAgentError(RuntimeError):
    """Base error for the local computer-control layer."""


class ApprovalRequired(ComputerAgentError):
    """Raised when an action needs an explicit human approval flag."""


class CapabilityUnavailable(ComputerAgentError):
    """Raised when an optional browser/desktop dependency is unavailable."""


class WorkspaceBoundaryError(ComputerAgentError):
    """Raised when a command attempts to select a cwd outside the workspace."""


@dataclass(frozen=True)
class CapabilityStatus:
    shell: bool
    browser: bool
    desktop: bool
    platform: str
    workspace: str


_SAFE_SHELL_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("pwd",),
    ("ls",),
    ("find",),
    ("cat",),
    ("head",),
    ("tail",),
    ("wc",),
    ("grep",),
    ("rg",),
    ("git", "status"),
    ("git", "diff"),
    ("git", "log"),
    ("git", "show"),
    ("python", "--version"),
    ("python3", "--version"),
    ("node", "--version"),
    ("npm", "--version"),
    ("pytest",),
)

_BLOCKED_SHELL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\brm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)",
        r"\bmkfs(?:\.|\s)",
        r"\b(?:fdisk|parted)\b",
        r"\bdd\s+[^\n]*\bof=/dev/",
        r"\b(?:shutdown|reboot|halt|poweroff)\b",
        r":\(\)\s*\{\s*:\|:\s*&\s*\}\s*;\s*:",
        r"\bchmod\s+-R\s+777\s+/\b",
    )
)


def classify_shell_command(command: str) -> str:
    """Return ``safe``, ``approval``, or ``blocked`` for a shell command."""
    stripped = command.strip()
    if not stripped:
        return "blocked"
    if any(pattern.search(stripped) for pattern in _BLOCKED_SHELL_PATTERNS):
        return "blocked"
    if any(token in stripped for token in (";", "&&", "||", "|", ">", "<", "`", "$(")):
        return "approval"
    try:
        argv = tuple(shlex.split(stripped))
    except ValueError:
        return "approval"
    if not argv:
        return "blocked"
    for prefix in _SAFE_SHELL_PREFIXES:
        if argv[: len(prefix)] == prefix:
            return "safe"
    return "approval"


class ComputerToolbox:
    """Local browser, shell, filesystem-adjacent, and desktop action tools."""

    def __init__(self, workspace_root: str | Path, *, headless: bool | None = None) -> None:
        self.workspace = Path(workspace_root).expanduser().resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.headless = bool(headless) if headless is not None else os.getenv("GPT_DOUG_HEADLESS", "0") == "1"
        self._playwright = None
        self._browser = None
        self._page = None

    def status(self) -> dict[str, Any]:
        result = CapabilityStatus(
            shell=True,
            browser=importlib.util.find_spec("playwright") is not None,
            desktop=importlib.util.find_spec("pyautogui") is not None,
            platform=f"{platform.system()} {platform.machine()}",
            workspace=str(self.workspace),
        )
        return asdict(result)

    def _resolve_cwd(self, cwd: str = ".") -> Path:
        target = (self.workspace / cwd).resolve()
        if target != self.workspace and self.workspace not in target.parents:
            raise WorkspaceBoundaryError("cwd escapes GPT-DOUG workspace")
        if not target.exists() or not target.is_dir():
            raise WorkspaceBoundaryError(f"cwd is not a directory: {cwd}")
        return target

    @staticmethod
    def _require_approval(action: str, approve: bool) -> None:
        if not approve:
            raise ApprovalRequired(f"{action} requires approve=True")

    def run_shell(
        self,
        command: str,
        *,
        cwd: str = ".",
        timeout: int = 120,
        approve: bool = False,
        max_output: int = 32_000,
    ) -> dict[str, Any]:
        risk = classify_shell_command(command)
        if risk == "blocked":
            raise ComputerAgentError("command is blocked by the Clawbot Mode host-safety policy")
        if risk == "approval":
            self._require_approval("shell command", approve)
        if timeout < 1 or timeout > 900:
            raise ValueError("timeout must be between 1 and 900 seconds")
        workdir = self._resolve_cwd(cwd)
        proc = subprocess.run(
            ["/bin/bash", "-lc", command],
            cwd=workdir,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=os.environ.copy(),
            check=False,
        )
        stdout = proc.stdout[-max_output:]
        stderr = proc.stderr[-max_output:]
        return {
            "command": command,
            "risk": risk,
            "cwd": str(workdir),
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": len(proc.stdout) > max_output or len(proc.stderr) > max_output,
        }

    @staticmethod
    def _validate_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ComputerAgentError("browser URLs must use http:// or https://")
        return url

    def _ensure_browser(self) -> Any:
        if self._page is not None:
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise CapabilityUnavailable(
                "browser control needs Playwright: pip install playwright && playwright install chromium"
            ) from error
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        context = self._browser.new_context(accept_downloads=True)
        self._page = context.new_page()
        return self._page

    def browser_open(self, url: str) -> dict[str, Any]:
        page = self._ensure_browser()
        page.goto(self._validate_url(url), wait_until="domcontentloaded")
        return {"url": page.url, "title": page.title()}

    def browser_snapshot(self, *, max_chars: int = 20_000) -> dict[str, Any]:
        page = self._ensure_browser()
        text = page.locator("body").inner_text() if page.locator("body").count() else ""
        return {"url": page.url, "title": page.title(), "text": text[:max_chars], "truncated": len(text) > max_chars}

    def browser_click(self, selector: str, *, approve: bool = False) -> dict[str, Any]:
        self._require_approval("browser click", approve)
        page = self._ensure_browser()
        page.locator(selector).first.click()
        return {"clicked": selector, "url": page.url}

    def browser_type(self, selector: str, text: str, *, approve: bool = False) -> dict[str, Any]:
        self._require_approval("browser typing", approve)
        page = self._ensure_browser()
        target = page.locator(selector).first
        target.fill(text)
        return {"typed": selector, "characters": len(text), "url": page.url}

    def browser_screenshot(self, path: str = "artifacts/gpt-doug-screen.png", *, full_page: bool = True) -> dict[str, Any]:
        page = self._ensure_browser()
        target = (self.workspace / path).resolve()
        if target != self.workspace and self.workspace not in target.parents:
            raise WorkspaceBoundaryError("screenshot path escapes GPT-DOUG workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(target), full_page=full_page)
        return {"path": str(target.relative_to(self.workspace)), "url": page.url}

    def browser_close(self) -> dict[str, Any]:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = self._browser = self._page = None
        return {"closed": True}

    def _pyautogui(self) -> Any:
        try:
            import pyautogui
        except ImportError as error:
            raise CapabilityUnavailable("desktop control needs pyautogui: pip install pyautogui") from error
        return pyautogui

    def desktop_screenshot(self, path: str = "artifacts/desktop.png") -> dict[str, Any]:
        target = (self.workspace / path).resolve()
        if target != self.workspace and self.workspace not in target.parents:
            raise WorkspaceBoundaryError("desktop screenshot path escapes GPT-DOUG workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._pyautogui().screenshot(str(target))
        return {"path": str(target.relative_to(self.workspace))}

    def desktop_click(self, x: int, y: int, *, approve: bool = False) -> dict[str, Any]:
        self._require_approval("desktop click", approve)
        self._pyautogui().click(x=x, y=y)
        return {"clicked": [x, y]}

    def desktop_type(self, text: str, *, interval: float = 0.01, approve: bool = False) -> dict[str, Any]:
        self._require_approval("desktop typing", approve)
        self._pyautogui().write(text, interval=interval)
        return {"characters": len(text)}

    def desktop_hotkey(self, keys: Iterable[str], *, approve: bool = False) -> dict[str, Any]:
        self._require_approval("desktop hotkey", approve)
        key_list = list(keys)
        if not key_list:
            raise ValueError("keys must not be empty")
        self._pyautogui().hotkey(*key_list)
        return {"keys": key_list}


def attach_computer_tools(runtime: Any, toolbox: ComputerToolbox | None = None) -> ComputerToolbox:
    """Register Clawbot Mode tools on an existing Wakeup3LM runtime."""
    if toolbox is None:
        toolbox = ComputerToolbox(runtime.workspace.root)
    runtime.tools.update(
        {
            "computer_status": toolbox.status,
            "run_shell": toolbox.run_shell,
            "browser_open": toolbox.browser_open,
            "browser_snapshot": toolbox.browser_snapshot,
            "browser_click": toolbox.browser_click,
            "browser_type": toolbox.browser_type,
            "browser_screenshot": toolbox.browser_screenshot,
            "browser_close": toolbox.browser_close,
            "desktop_screenshot": toolbox.desktop_screenshot,
            "desktop_click": toolbox.desktop_click,
            "desktop_type": toolbox.desktop_type,
            "desktop_hotkey": toolbox.desktop_hotkey,
        }
    )
    runtime.ontology.upsert(
        "ComputerAgent",
        "gpt-doug-clawbot",
        architecture="local-capability-gated",
        workspace=str(toolbox.workspace),
        capabilities=toolbox.status(),
    )
    runtime.ontology.link("Model", "wakeup3lm", "USES", "ComputerAgent", "gpt-doug-clawbot")
    return toolbox


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpt-doug-clawbot", description="GPT-DOUG local computer agent tools")
    parser.add_argument("--workspace", default=".", help="workspace boundary (default: current directory)")
    parser.add_argument("--headless", action="store_true", help="run managed Chromium headless")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="show available local capabilities")

    shell = sub.add_parser("shell", help="run a shell command inside the workspace")
    shell.add_argument("--approve", action="store_true", help="approve a command classified as side-effecting")
    shell.add_argument("command", nargs=argparse.REMAINDER)

    browser = sub.add_parser("browser-open", help="open a URL with managed Chromium")
    browser.add_argument("url")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    toolbox = ComputerToolbox(args.workspace, headless=args.headless)
    try:
        if args.action == "status":
            result = toolbox.status()
        elif args.action == "shell":
            command = " ".join(args.command).strip()
            result = toolbox.run_shell(command, approve=args.approve)
        elif args.action == "browser-open":
            result = toolbox.browser_open(args.url)
        else:
            raise ComputerAgentError(f"unknown action: {args.action}")
        print(json.dumps(result, indent=2, default=str))
        return 0
    except (ComputerAgentError, subprocess.TimeoutExpired, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 2
    finally:
        toolbox.browser_close()


if __name__ == "__main__":
    raise SystemExit(main())
