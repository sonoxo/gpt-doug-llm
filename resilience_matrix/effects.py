"""Standard-library terminal animations for The Resilience Matrix."""

from __future__ import annotations

import math
import os
import shutil
import sys
import time
from typing import Callable, Dict, List, Optional, TextIO, Tuple


class TerminalFX:
    """ANSI-aware terminal effects with a quiet non-TTY fallback."""

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
        (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0),
        (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
        (-1.0, -1.0, 1.0), (1.0, -1.0, 1.0),
        (1.0, 1.0, 1.0), (-1.0, 1.0, 1.0),
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
        scene_seconds: float = 3.0,
        fps: int = 24,
    ) -> None:
        self.stream = stream or sys.stdout
        self.sleep = sleep
        self.three_d = bool(three_d)
        self.scene_seconds = self._validate_seconds(scene_seconds)
        self.fps = self._validate_fps(fps)
        self.supported = self._terminal_supports_animation()
        self.enabled = bool(enabled) and self.supported
        self._refresh_color()

    @staticmethod
    def _validate_seconds(seconds: float) -> float:
        value = float(seconds)
        if value <= 0:
            raise ValueError("3D scene duration must be greater than zero")
        return value

    @staticmethod
    def _validate_fps(fps: int) -> int:
        value = int(fps)
        if value < 6 or value > 60:
            raise ValueError("3D FPS must be between 6 and 60")
        return value

    def _terminal_supports_animation(self) -> bool:
        is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        disabled = (
            os.environ.get("TERM", "").lower() == "dumb"
            or os.environ.get("RESILIENCE_NO_ANIMATIONS", "").lower()
            in {"1", "true", "yes", "on"}
        )
        return is_tty and not disabled

    def _refresh_color(self) -> None:
        self.color = self.enabled and "NO_COLOR" not in os.environ

    def set_enabled(self, enabled: bool) -> bool:
        self.enabled = bool(enabled) and self.supported
        self._refresh_color()
        return self.enabled

    def set_scene_seconds(self, seconds: float) -> float:
        self.scene_seconds = self._validate_seconds(seconds)
        return self.scene_seconds

    def set_fps(self, fps: int) -> int:
        self.fps = self._validate_fps(fps)
        return self.fps

    def settings(self) -> Dict[str, object]:
        return {
            "supported": self.supported,
            "enabled": self.enabled,
            "three_d": self.three_d,
            "scene_seconds": self.scene_seconds,
            "fps": self.fps,
            "color": self.color,
        }

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

    def _project_cube(self, angle: float, width: int, height: int) -> List[Tuple[int, int]]:
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

        for corner in ((1, 1), (width - 2, 1), (width - 2, height - 2), (1, height - 2)):
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

    def scene3d(self, label: str, *, seconds: Optional[float] = None) -> None:
        if not self.enabled or not self.three_d:
            return
        duration = self.scene_seconds if seconds is None else self._validate_seconds(seconds)
        frames = max(1, round(duration * self.fps))
        delay = duration / frames
        self._write(self.ALT_SCREEN_ON + self.HIDE_CURSOR)
        try:
            for index in range(frames):
                angle = index * (2 * math.pi / frames) * 1.4
                frame = self._render_3d_frame(angle, label)
                if self.color:
                    frame = self.CYAN + frame + self.RESET
                self._write(self.HOME + self.CLEAR_SCREEN + frame)
                self.sleep(delay)
        finally:
            self._write(self.RESET + self.SHOW_CURSOR + self.ALT_SCREEN_OFF)

    def showcase(self, seconds: Optional[float] = None) -> None:
        if not self.enabled:
            return
        if self.three_d:
            self.scene3d("MANUAL EFFECTS SHOWCASE", seconds=seconds)
        self.phase("Terminal effects channel", frames=8, delay=0.02, final="ONLINE")

    def boot(self) -> None:
        if not self.enabled:
            return
        self.scene3d("ONTOLOGY LINK ESTABLISHED")
        self._write("\n")
        self.phase("Loading ontology graph", frames=7, final="LINKED")
        self.phase("Calibrating ordinal risk matrix", frames=8, final="CALIBRATED")
        self.phase("Synchronizing control evidence", frames=7, final="VERIFIED")
        self.phase("Opening resilience command channel", frames=8, final="ONLINE")
        self._write("\n")

    def turn(self, turn: int, total: int, title: str) -> None:
        if not self.enabled:
            return
        self.scene3d(f"TURN {turn}/{total} // {title}")
        self.phase(f"TURN {turn}/{total} :: {title}", frames=6, delay=0.018, width=16, final="EVENT")

    def decision(self) -> None:
        if not self.enabled:
            return
        self.scene3d("DEFENSIVE DECISION RESOLUTION")
        self.phase("Applying defensive decision", frames=6, delay=0.02, width=16, final="APPLIED")
        self.phase("Recalculating resilience posture", frames=7, delay=0.018, width=16, final="UPDATED")

    def io(self, label: str, final: str) -> None:
        if not self.enabled:
            return
        self.phase(label, frames=5, delay=0.018, width=14, final=final)

    def finale(self) -> None:
        if not self.enabled:
            return
        self.scene3d("EXECUTIVE ASSESSMENT // FINAL")
        self.phase("Compiling executive assessment", frames=9, delay=0.02, width=20, final="COMPLETE")
