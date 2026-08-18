"""Standard-library terminal animations for The Resilience Matrix."""

from __future__ import annotations

import math
import os
import shutil
import sys
import time
from typing import Callable, List, Optional, TextIO, Tuple


class TerminalFX:
    """ANSI-aware terminal effects with a quiet non-TTY fallback.

    Interactive terminals use pseudo-3D wireframe scenes by default. The scenes
    run in the terminal's alternate screen buffer so normal game output is not
    erased. Redirected output, CI, TERM=dumb, or RESILIENCE_NO_ANIMATIONS
    disables animation cleanly. NO_COLOR suppresses ANSI color only.
    """

    SPINNER = ("|", "/", "-", "\\")
    HIDE_CURSOR = "\x1b[?25l"
    SHOW_CURSOR = "\x1b[?25h"
    CLEAR_LINE = "\x1b[2K"
    CLEAR_SCREEN = "\x1b[2J"
    HOME = "\x1b[H"
    ALT_SCREEN_ON = "\x1b[?1049h"
    ALT_SCREEN_OFF = "\x1b[?1049l"
    DIM = "\x1b[2m"
    BOLD = "\x1b[1m"
    CYAN = "\x1b[36m"
    RESET = "\x1b[0m"

    CUBE_VERTICES: Tuple[Tuple[float, float, float], ...] = (
        (-1.0, -1.0, -1.0),
        (1.0, -1.0, -1.0),
        (1.0, 1.0, -1.0),
        (-1.0, 1.0, -1.0),
        (-1.0, -1.0, 1.0),
        (1.0, -1.0, 1.0),
        (1.0, 1.0, 1.0),
        (-1.0, 1.0, 1.0),
    )
    CUBE_EDGES: Tuple[Tuple[int, int], ...] = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )

    def __init__(
        self,
        enabled: bool = True,
        stream: Optional[TextIO] = None,
        sleep: Callable[[float], None] = time.sleep,
        three_d: bool = True,
    ) -> None:
        self.stream = stream or sys.stdout
        self.sleep = sleep
        self.three_d = bool(three_d)
        self.enabled = bool(enabled) and self._terminal_supports_animation()
        self.color = self.enabled and "NO_COLOR" not in os.environ

    def _terminal_supports_animation(self) -> bool:
        is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        disabled = (
            os.environ.get("TERM", "").lower() == "dumb"
            or os.environ.get("RESILIENCE_NO_ANIMATIONS", "").lower()
            in {"1", "true", "yes", "on"}
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

    @staticmethod
    def _draw_line(
        canvas: List[List[str]],
        start: Tuple[int, int],
        end: Tuple[int, int],
        char: str,
    ) -> None:
        """Draw a clipped Bresenham line into an ASCII canvas."""
        x0, y0 = start
        x1, y1 = end
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        height = len(canvas)
        width = len(canvas[0]) if height else 0
        while True:
            if 0 <= x0 < width and 0 <= y0 < height:
                canvas[y0][x0] = char
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * error
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy

    def _project_cube(
        self,
        angle: float,
        width: int,
        height: int,
    ) -> List[Tuple[int, int]]:
        cy = math.cos(angle * 0.73)
        sy = math.sin(angle * 0.73)
        cx = math.cos(angle * 0.47)
        sx = math.sin(angle * 0.47)
        center_x = width // 2
        center_y = height // 2
        focal = min(width * 0.64, height * 2.0)
        projected: List[Tuple[int, int]] = []
        for x, y, z in self.CUBE_VERTICES:
            xr = x * cy - z * sy
            zr = x * sy + z * cy
            yr = y * cx - zr * sx
            zr = y * sx + zr * cx + 4.4
            px = center_x + int((xr * focal) / zr)
            py = center_y + int((yr * focal * 0.48) / zr)
            projected.append((px, py))
        return projected

    def _render_3d_frame(self, angle: float, label: str) -> str:
        """Render one perspective tunnel plus rotating wireframe cube frame."""
        terminal = shutil.get_terminal_size(fallback=(80, 24))
        width = max(48, min(78, terminal.columns - 2))
        height = max(17, min(23, terminal.lines - 3))
        canvas = [[" " for _ in range(width)] for _ in range(height)]
        center = (width // 2, height // 2)

        pulse = (math.sin(angle * 1.4) + 1.0) / 2.0
        for depth in range(5):
            t = (depth + pulse) / 6.0
            left = int(2 + (center[0] - 7) * t)
            right = width - 1 - left
            top = int(1 + (center[1] - 3) * t)
            bottom = height - 2 - top
            if right <= left or bottom <= top:
                continue
            self._draw_line(canvas, (left, top), (right, top), ".")
            self._draw_line(canvas, (right, top), (right, bottom), ".")
            self._draw_line(canvas, (right, bottom), (left, bottom), ".")
            self._draw_line(canvas, (left, bottom), (left, top), ".")

        corners = (
            (1, 1),
            (width - 2, 1),
            (width - 2, height - 2),
            (1, height - 2),
        )
        for corner in corners:
            self._draw_line(canvas, corner, center, ":")

        points = self._project_cube(angle, width, height)
        for first, second in self.CUBE_EDGES:
            self._draw_line(canvas, points[first], points[second], "#")
        for x, y in points:
            if 0 <= x < width and 0 <= y < height:
                canvas[y][x] = "O"

        title = " RESILIENCE MATRIX // 3D CHANNEL "
        start = max(0, (width - len(title)) // 2)
        for index, char in enumerate(title[:width]):
            canvas[0][start + index] = char

        footer = f" {label} "[: max(1, width - 4)]
        footer_start = max(0, (width - len(footer)) // 2)
        for index, char in enumerate(footer):
            canvas[-1][footer_start + index] = char

        return "\n".join("".join(row).rstrip() for row in canvas)

    def scene3d(
        self,
        label: str,
        *,
        frames: int = 14,
        delay: float = 0.035,
    ) -> None:
        """Show a short pseudo-3D cinematic in the alternate screen buffer."""
        if not self.enabled or not self.three_d:
            return
        self._write(self.ALT_SCREEN_ON + self.HIDE_CURSOR)
        try:
            for index in range(max(1, frames)):
                angle = index * 0.22
                frame = self._render_3d_frame(angle, label)
                if self.color:
                    frame = self.CYAN + frame + self.RESET
                self._write(self.HOME + self.CLEAR_SCREEN + frame)
                self.sleep(delay)
        finally:
            self._write(self.RESET + self.SHOW_CURSOR + self.ALT_SCREEN_OFF)

    def boot(self) -> None:
        """Run the startup sequence."""
        if not self.enabled:
            return
        self.scene3d("ONTOLOGY LINK ESTABLISHED", frames=16, delay=0.03)
        self._write("\n")
        self.phase("Loading ontology graph", frames=7, final="LINKED")
        self.phase("Calibrating ordinal risk matrix", frames=8, final="CALIBRATED")
        self.phase("Synchronizing control evidence", frames=7, final="VERIFIED")
        self.phase("Opening resilience command channel", frames=8, final="ONLINE")
        self._write("\n")

    def turn(self, turn: int, total: int, title: str) -> None:
        if not self.enabled:
            return
        self.scene3d(f"TURN {turn}/{total} // {title}", frames=9, delay=0.025)
        self.phase(
            f"TURN {turn}/{total} :: {title}",
            frames=6,
            delay=0.018,
            width=16,
            final="EVENT",
        )

    def decision(self) -> None:
        if not self.enabled:
            return
        self.scene3d("DEFENSIVE DECISION RESOLUTION", frames=10, delay=0.025)
        self.phase(
            "Applying defensive decision",
            frames=6,
            delay=0.02,
            width=16,
            final="APPLIED",
        )
        self.phase(
            "Recalculating resilience posture",
            frames=7,
            delay=0.018,
            width=16,
            final="UPDATED",
        )

    def io(self, label: str, final: str) -> None:
        if not self.enabled:
            return
        self.phase(label, frames=5, delay=0.018, width=14, final=final)

    def finale(self) -> None:
        if not self.enabled:
            return
        self.scene3d("EXECUTIVE ASSESSMENT // FINAL", frames=15, delay=0.03)
        self.phase(
            "Compiling executive assessment",
            frames=9,
            delay=0.02,
            width=20,
            final="COMPLETE",
        )
