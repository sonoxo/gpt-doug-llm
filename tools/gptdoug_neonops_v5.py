#!/usr/bin/env python3
"""GPT-Doug NeonOps V5 dashboard.

A dynamic vaporwave/UNIX command-center panel for macOS Terminal + tmux.
It reports real local state while presenting it with a Linux-vaporwave visual language.
"""
from __future__ import annotations

import json
import math
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path.home() / "gpt-doug-llm"
STATE_FILE = Path.home() / ".gpt-doug" / "max-shell-state.json"
EMOTE_FILE = Path.home() / ".gpt-doug" / "visual-emote.json"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
HOME = "\033[H"
CLEAR = "\033[2J"

PINK = "\033[38;2;255;50;205m"
HOT = "\033[38;2;255;80;125m"
PURPLE = "\033[38;2;190;100;255m"
BLUE = "\033[38;2;75;120;255m"
CYAN = "\033[38;2;0;235;255m"
AQUA = "\033[38;2;50;255;220m"
GREEN = "\033[38;2;60;255;145m"
YELLOW = "\033[38;2;255;220;80m"
WHITE = "\033[38;2;235;245;255m"
GRAY = "\033[38;2;110;125;150m"

PALETTE = [CYAN, PINK, PURPLE, AQUA, BLUE]


def sh(*argv: str) -> str:
    try:
        proc = subprocess.run(
            argv,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=1.2,
            check=False,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {
        "state": "IDLE",
        "provider": "none",
        "model": "unknown",
        "detail": "waiting for GPT-Doug",
    }


def emote_state() -> str:
    try:
        data = json.loads(EMOTE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            until = float(data.get("until", 0) or 0)
            if until and time.time() > until:
                return "auto"
            return str(data.get("name", "auto")).strip().lower() or "auto"
    except Exception:
        return "auto"


def safe_width() -> int:
    return max(34, shutil.get_terminal_size((46, 52)).columns - 1)


def clip(text: str, width: int) -> str:
    return text[: max(1, width)]


def meter(value: float, width: int = 14) -> str:
    value = max(0.0, min(1.0, value))
    filled = int(round(value * width))
    return CYAN + "▰" * filled + PURPLE + "▱" * (width - filled) + RESET


def led(ok: bool) -> str:
    return (GREEN + "●" if ok else HOT + "●") + RESET


def wave(t: float, width: int) -> str:
    chars = " ▁▂▃▄▅▆▇█"
    out = []
    for x in range(width):
        y = (
            math.sin(t * 3.0 + x * 0.52)
            + 0.55 * math.sin(t * 5.2 + x * 0.23)
        )
        idx = int((y + 1.55) / 3.1 * (len(chars) - 1))
        idx = max(0, min(len(chars) - 1, idx))
        out.append(chars[idx])
    return CYAN + "".join(out) + RESET


def neon_sun(width: int, t: float) -> list[str]:
    radius = max(4, min(8, width // 5))
    cx = width // 2
    rows = []
    for yy in range(-radius, radius + 1):
        rel = yy / radius
        half = int(radius * math.sqrt(max(0.0, 1.0 - rel * rel)))
        chars = [" "] * width
        for x in range(max(0, cx - half), min(width, cx + half + 1)):
            if (yy + radius + int(t * 3)) % 4 == 2:
                chars[x] = "─"
            elif yy < 0:
                chars[x] = "█"
            else:
                chars[x] = "▓"
        color = PINK if yy < 0 else (HOT if yy < radius * 0.45 else PURPLE)
        rows.append(color + "".join(chars) + RESET)
    return rows


def perspective_grid(width: int, rows: int, t: float) -> list[str]:
    out = []
    center = width // 2
    for y in range(rows):
        depth = (y + 1) / max(1, rows)
        chars = [" "] * width
        if (y + int(t * 5)) % 2 == 0:
            for x in range(width):
                chars[x] = "─"
        spacing = max(5, int(16 * (1 - depth) + 4))
        for offset in range(-width, width + 1, spacing):
            x = int(center + offset * depth)
            if 0 <= x < width:
                chars[x] = "╱" if x < center else ("╲" if x > center else "│")
        out.append(PURPLE + "".join(chars) + RESET)
    return out


def main() -> int:
    start = time.monotonic()
    print(CLEAR + HIDE, end="", flush=True)
    try:
        while True:
            t = time.monotonic() - start
            width = safe_width()
            s = state()

            mode = str(s.get("state", "IDLE")).upper()
            provider = str(s.get("provider", "none"))
            model = str(s.get("model", "unknown"))
            detail = str(s.get("detail", ""))
            emote = emote_state()

            branch = sh("git", "branch", "--show-current") or "detached"
            commit = sh("git", "rev-parse", "--short", "HEAD") or "-------"
            dirty = bool(sh("git", "status", "--short"))
            ollama_models = sh("ollama", "list") if shutil.which("ollama") else ""
            ollama_ok = bool(ollama_models)
            brain_ok = provider.lower() not in {"", "none", "unknown", "offline"}
            xunia_ok = (ROOT / "xunia_godis.py").exists()
            zyra_ok = (ROOT / "zyra_agent.py").exists()
            swarm_ok = (ROOT / "workers" / "revenue_swarm.py").exists()
            visual_ok = (ROOT / "tools" / "gptdoug_supreme_visual_v4.py").exists()
            voice_ok = shutil.which("say") is not None

            try:
                load = os.getloadavg()[0]
            except Exception:
                load = 0.0
            disk = shutil.disk_usage(ROOT)
            disk_used = 1.0 - disk.free / max(1, disk.total)

            color = PALETTE[int(t * 2.5) % len(PALETTE)]
            blink = "◆" if int(t * 4) % 2 else "◇"

            lines: list[str] = []
            lines += [
                color + BOLD + "╭─[ NEONOPS // VAPORWAVE UNIX ]─╮" + RESET,
                color + f"│ {blink} GPT-DOUG // DREAM MACHINE" + RESET,
                color + "╰─────────────────────────────────╯" + RESET,
                GRAY + "Darwin host // Linux-vaporwave soul" + RESET,
                "",
            ]

            lines += neon_sun(width, t)
            lines.append(CYAN + "─" * width + RESET)
            lines += perspective_grid(width, 5, t)
            lines.append("")

            lines += [
                PINK + BOLD + "🧠 XUNIA / ZYRA / DOUG" + RESET,
                f" {led(brain_ok)} brain    {CYAN}{provider}{RESET}",
                f" {led(xunia_ok)} XUNIA    {'ONLINE' if xunia_ok else 'MISSING'}",
                f" {led(zyra_ok)} ZYRA     {'ONLINE' if zyra_ok else 'MISSING'}",
                f" {led(swarm_ok)} swarm    {'READY' if swarm_ok else 'MISSING'}",
                f" {led(visual_ok)} visual   {'ONLINE' if visual_ok else 'MISSING'}",
                f" {led(voice_ok)} voice    {'READY' if voice_ok else 'MISSING'}",
                "",
                AQUA + BOLD + "⚡ LIVE STATE" + RESET,
                f" mode    {color}{mode}{RESET}",
                f" model   {PURPLE}{clip(model, max(12, width-9))}{RESET}",
                f" detail  {GRAY}{clip(detail, max(12, width-9))}{RESET}",
                f" emote   {PINK}{clip(emote, max(12, width-9))}{RESET}",
                "",
                WHITE + BOLD + "📟 MACHINE" + RESET,
                f" load    {meter(min(1.0, load / 8.0))} {load:.2f}",
                f" disk    {meter(disk_used)}",
                f" host    {CYAN}{clip(platform.node(), 20)}{RESET}",
                f" os      {PURPLE}{platform.system()} {clip(platform.release(), 11)}{RESET}",
                "",
                WHITE + BOLD + "🗂 GIT REALITY" + RESET,
                f" branch  {CYAN}{clip(branch, 21)}{RESET}",
                f" commit  {PINK}{commit}{RESET}",
                f" tree    {(YELLOW + 'DIRTY') if dirty else (GREEN + 'CLEAN')}{RESET}",
                "",
                PINK + BOLD + "〰 SIGNAL" + RESET,
                wave(t, min(width, 28)),
                "",
                GRAY + "∞ dream // build // test // speak // repeat" + RESET,
            ]

            output = HOME
            max_rows = shutil.get_terminal_size((46, 52)).lines
            for line in lines[:max_rows]:
                output += clip(line, width * 7) + "\033[K\n"
            output += "\033[J"
            print(output, end="", flush=True)
            time.sleep(0.125)
    except KeyboardInterrupt:
        return 0
    finally:
        print(RESET + SHOW, end="", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
