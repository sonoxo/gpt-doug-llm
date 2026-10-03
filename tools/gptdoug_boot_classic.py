#!/usr/bin/env python3
"""GPT-Doug Classic Boot.

A terminal-native boot sequence inspired by early compact-computer startup screens.
No external dependencies.
"""
from __future__ import annotations

import os
import shutil
import signal
import sys
import time

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLACK = "\033[38;2;20;20;20m"
WHITE = "\033[38;2;238;238;230m"
GRAY = "\033[38;2;150;150;145m"
RED = "\033[38;2;255;80;78m"
ORANGE = "\033[38;2;255;160;50m"
YELLOW = "\033[38;2;255;220;70m"
GREEN = "\033[38;2;70;220;120m"
CYAN = "\033[38;2;0;220;255m"
BLUE = "\033[38;2;70;110;255m"
PURPLE = "\033[38;2;185;90;255m"
MAGENTA = "\033[38;2;255;60;210m"

CLEAR = "\033[2J"
HOME = "\033[H"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
ALT_ON = "\033[?1049h"
ALT_OFF = "\033[?1049l"

running = True


def stop(*_args):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


MAC_OPEN = [
    "        ╭──────────────────╮",
    "        │  ╭────────────╮  │",
    "        │  │  ▄      ▄  │  │",
    "        │  │            │  │",
    "        │  │    ▀▀▀     │  │",
    "        │  │  ╰──────╯  │  │",
    "        │  ╰────────────╯  │",
    "        │                  │",
    "        │  ▬▬▬       ▯     │",
    "        ╰──────────────────╯",
    "            ▔▔▔▔▔▔▔▔",
]

MAC_BLINK = [
    "        ╭──────────────────╮",
    "        │  ╭────────────╮  │",
    "        │  │  ─      ─  │  │",
    "        │  │            │  │",
    "        │  │    ▀▀▀     │  │",
    "        │  │  ╰──────╯  │  │",
    "        │  ╰────────────╯  │",
    "        │                  │",
    "        │  ▬▬▬       ▯     │",
    "        ╰──────────────────╯",
    "            ▔▔▔▔▔▔▔▔",
]

STAGES = [
    ("ROM", "terminal fabric"),
    ("XUNIA", "reasoning core"),
    ("ZYRA", "agent runtime"),
    ("DOUG", "master directive"),
    ("VISION", "facial cortex"),
    ("VOICE", "speech interface"),
    ("DREAM", "dreamwave shell"),
]


def term_size():
    return shutil.get_terminal_size((100, 36))


def center(text: str, width: int) -> str:
    return " " * max(0, (width - len(text)) // 2) + text


def draw_logo(lines: list[str], top: int, width: int) -> str:
    out = []
    for i, line in enumerate(lines):
        out.append(f"\033[{top+i};1H" + center(line, width) + "\033[K")
    return "".join(out)


def color_rainbow(width: int) -> str:
    blocks = [
        (RED, "██"),
        (ORANGE, "██"),
        (YELLOW, "██"),
        (GREEN, "██"),
        (CYAN, "██"),
        (BLUE, "██"),
        (PURPLE, "██"),
    ]
    strip = "".join(c + b for c, b in blocks) + RESET
    return center(strip, width)


def progress_bar(value: float, width: int = 34) -> str:
    value = max(0.0, min(1.0, value))
    n = int(round(width * value))
    return "[" + WHITE + "█" * n + GRAY + "░" * (width - n) + RESET + "]"


def main() -> int:
    fast = os.environ.get("GPT_DOUG_BOOT_FAST", "0").lower() in {"1", "true", "yes"}
    step_delay = 0.10 if fast else 0.18
    cols, rows = term_size()
    top = max(2, rows // 2 - 12)

    sys.stdout.write(ALT_ON + CLEAR + HOME + HIDE)
    sys.stdout.flush()

    try:
        started = time.monotonic()
        last_blink = 0.0

        # Logo materializes.
        for pct in (0.0, 0.18, 0.34):
            if not running:
                return 130
            sys.stdout.write(draw_logo(MAC_OPEN, top, cols))
            sys.stdout.write(f"\033[{top+12};1H" + center(BOLD + WHITE + "GPT-DOUG" + RESET, cols) + "\033[K")
            sys.stdout.write(f"\033[{top+14};1H" + center(progress_bar(pct), cols) + "\033[K")
            sys.stdout.flush()
            time.sleep(step_delay)

        # System pipeline.
        for index, (name, detail) in enumerate(STAGES, start=1):
            if not running:
                return 130

            elapsed = time.monotonic() - started
            blink = elapsed - last_blink > 0.7 and index in {2, 5}
            if blink:
                sys.stdout.write(draw_logo(MAC_BLINK, top, cols))
                sys.stdout.flush()
                time.sleep(0.07)
                sys.stdout.write(draw_logo(MAC_OPEN, top, cols))
                last_blink = elapsed

            pct = index / len(STAGES)
            stage = f"{name:<7}  {detail}"
            sys.stdout.write(
                f"\033[{top+13};1H"
                + center(CYAN + stage + RESET, cols)
                + "\033[K"
            )
            sys.stdout.write(
                f"\033[{top+14};1H"
                + center(progress_bar(pct), cols)
                + "\033[K"
            )
            sys.stdout.flush()
            time.sleep(step_delay)

        # Classic rainbow signature appears only at completed boot.
        sys.stdout.write(f"\033[{top+9};1H" + color_rainbow(cols) + "\033[K")
        sys.stdout.write(
            f"\033[{top+12};1H"
            + center(BOLD + WHITE + "GPT-DOUG" + RESET, cols)
            + "\033[K"
        )
        sys.stdout.write(
            f"\033[{top+13};1H"
            + center(MAGENTA + "Welcome to the Dreamwave Terminal." + RESET, cols)
            + "\033[K"
        )
        sys.stdout.write(
            f"\033[{top+14};1H"
            + center(progress_bar(1.0), cols)
            + "\033[K"
        )
        sys.stdout.flush()
        time.sleep(0.45 if fast else 0.85)
        return 0
    finally:
        sys.stdout.write(RESET + SHOW + ALT_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
