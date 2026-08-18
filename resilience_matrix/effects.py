"""Small standard-library terminal animations for The Resilience Matrix."""

from __future__ import annotations

import os
import sys
import time
from typing import Callable, Optional, TextIO


class TerminalFX:
    """ANSI-aware terminal effects with a quiet non-TTY fallback."""

    SPINNER = ("|", "/", "-", "\\")
    HIDE_CURSOR = "\x1b[?25l"
    SHOW_CURSOR = "\x1b[?25h"
    CLEAR_LINE = "\x1b[2K"
    DIM = "\x1b[2m"
    BOLD = "\x1b[1m"
    RESET = "\x1b[0m"

    def __init__(
        self,
        enabled: bool = True,
        stream: Optional[TextIO] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.stream = stream or sys.stdout
        self.sleep = sleep
        self.enabled = bool(enabled) and self._terminal_supports_animation()

    def _terminal_supports_animation(self) -> bool:
        is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        disabled = (
            os.environ.get("TERM", "").lower() == "dumb"
            or os.environ.get("RESILIENCE_NO_ANIMATIONS", "").lower() in {"1", "true", "yes", "on"}
        )
        return is_tty and not disabled

    def _write(self, text: str) -> None:
        self.stream.write(text)
        self.stream.flush()

    def phase(
        self,
        label: str,
        *,
        frames: int = 10,
        delay: float = 0.025,
        width: int = 18,
        final: str = "READY",
    ) -> None:
        """Animate a spinner/progress bar and finish with one stable status line."""
        if not self.enabled:
            return
        frames = max(1, frames)
        width = max(4, width)
        self._write(self.HIDE_CURSOR)
        try:
            for index in range(frames):
                filled = min(width, max(1, round(width * (index + 1) / frames)))
                bar = "#" * filled + "." * (width - filled)
                spinner = self.SPINNER[index % len(self.SPINNER)]
                self._write(
                    f"\r{self.CLEAR_LINE}{self.DIM}{spinner}{self.RESET} "
                    f"{label:<34} [{bar}]"
                )
                self.sleep(delay)
            self._write(
                f"\r{self.CLEAR_LINE}{self.BOLD}[{final}]{self.RESET} {label}\n"
            )
        finally:
            self._write(self.SHOW_CURSOR)

    def boot(self) -> None:
        """Run the startup sequence."""
        if not self.enabled:
            return
        self._write("\n")
        self.phase("Loading ontology graph", frames=9, final="LINKED")
        self.phase("Calibrating ordinal risk matrix", frames=10, final="CALIBRATED")
        self.phase("Synchronizing control evidence", frames=8, final="VERIFIED")
        self.phase("Opening resilience command channel", frames=10, final="ONLINE")
        self._write("\n")

    def turn(self, turn: int, total: int, title: str) -> None:
        if not self.enabled:
            return
        self.phase(
            f"TURN {turn}/{total} :: {title}",
            frames=8,
            delay=0.02,
            width=16,
            final="EVENT",
        )

    def decision(self) -> None:
        if not self.enabled:
            return
        self.phase(
            "Applying defensive decision",
            frames=8,
            delay=0.025,
            width=16,
            final="APPLIED",
        )
        self.phase(
            "Recalculating resilience posture",
            frames=9,
            delay=0.02,
            width=16,
            final="UPDATED",
        )

    def io(self, label: str, final: str) -> None:
        if not self.enabled:
            return
        self.phase(label, frames=6, delay=0.02, width=14, final=final)

    def finale(self) -> None:
        if not self.enabled:
            return
        self.phase(
            "Compiling executive assessment",
            frames=12,
            delay=0.025,
            width=20,
            final="COMPLETE",
        )
