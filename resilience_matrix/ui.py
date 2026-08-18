"""Presentation helpers for The Resilience Matrix terminal interface."""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from typing import Iterable, Mapping, Optional, TextIO


class TerminalUI:
    """Small dependency-free terminal UI with graceful plain-text fallback."""

    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    CYAN = "\x1b[36m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    MAGENTA = "\x1b[35m"
    WHITE = "\x1b[97m"
    GRAY = "\x1b[90m"

    RISK_COLORS = {
        "Low": GREEN,
        "Guarded": CYAN,
        "Elevated": YELLOW,
        "High": RED,
        "Extreme": RED + BOLD,
    }

    TRACK_ORDERS = {
        "readiness": ["Fragile", "Developing", "Prepared", "Resilient"],
        "budget": ["Depleted", "Constrained", "Guarded", "Adequate", "Strong"],
        "trust": ["Eroding", "Cautious", "Stable", "High"],
        "compliance": ["At Risk", "Watch", "Managed", "Strong"],
        "evidence_quality": ["Weak", "Partial", "Adequate", "Robust"],
    }

    def __init__(self, stream: Optional[TextIO] = None) -> None:
        self.stream = stream or sys.stdout
        self.is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.color = self.is_tty and "NO_COLOR" not in os.environ
        self.unicode = os.environ.get("TERM", "").lower() != "dumb"

    @property
    def width(self) -> int:
        columns = shutil.get_terminal_size(fallback=(88, 24)).columns
        return max(60, min(100, columns - 2))

    def paint(self, text: str, code: str) -> str:
        if not self.color:
            return text
        return f"{code}{text}{self.RESET}"

    def muted(self, text: str) -> str:
        return self.paint(text, self.GRAY)

    def title(self, text: str) -> str:
        return self.paint(text, self.BOLD + self.CYAN)

    def banner(self) -> None:
        w = self.width
        top, side, bottom = self._box_chars()
        print(top[0] + top[1] * (w - 2) + top[2], file=self.stream)
        print(side + self.title("THE RESILIENCE MATRIX").center(w - 2 + self._ansi_padding("THE RESILIENCE MATRIX")) + side, file=self.stream)
        subtitle = "DEFENSIVE GOVERNANCE // CYBER RESILIENCE // READINESS"
        print(side + self.paint(subtitle, self.DIM).center(w - 2 + self._ansi_padding(subtitle)) + side, file=self.stream)
        print(bottom[0] + bottom[1] * (w - 2) + bottom[2], file=self.stream)

    def _ansi_padding(self, raw: str) -> int:
        if not self.color:
            return 0
        return len(self.BOLD + self.CYAN + self.RESET) if raw == "THE RESILIENCE MATRIX" else len(self.DIM + self.RESET)

    def _box_chars(self):
        if self.unicode:
            return (("\u250f", "\u2501", "\u2513"), "\u2503", ("\u2517", "\u2501", "\u251b"))
        return (("+", "=", "+"), "|", ("+", "=", "+"))

    def section(self, label: str, title: str) -> None:
        label_text = self.paint(f" {label.upper()} ", self.BOLD + self.CYAN)
        raw_label = f" {label.upper()} "
        tail_width = max(3, self.width - len(raw_label) - len(title) - 4)
        rule = "\u2500" if self.unicode else "-"
        print(f"\n{label_text} {self.paint(title, self.BOLD)} {self.muted(rule * tail_width)}", file=self.stream)

    def paragraph(self, text: str, indent: int = 2) -> None:
        width = max(20, self.width - indent)
        for line in textwrap.wrap(str(text), width=width - indent) or [""]:
            print(" " * indent + line, file=self.stream)

    def bullets(self, items: Iterable[str], indent: int = 2) -> None:
        marker = "\u2022" if self.unicode else "-"
        for item in items:
            prefix = " " * indent + marker + " "
            continuation = " " * len(prefix)
            wrapped = textwrap.wrap(str(item), width=max(20, self.width - len(prefix))) or [""]
            print(prefix + wrapped[0], file=self.stream)
            for line in wrapped[1:]:
                print(continuation + line, file=self.stream)

    def badge(self, text: str, color: str = "") -> str:
        return self.paint(f"[{text}]", color or self.CYAN)

    def risk_badge(self, value: str) -> str:
        return self.badge(value.upper(), self.RISK_COLORS.get(value, self.CYAN))

    def track_meter(self, key: str, value: str, size: int = 5) -> str:
        order = self.TRACK_ORDERS.get(key, [])
        if value not in order:
            return value
        active = order.index(value) + 1
        filled_count = max(1, round(active / len(order) * size))
        if self.unicode:
            meter = "\u25cf" * filled_count + "\u25cb" * (size - filled_count)
        else:
            meter = "#" * filled_count + "." * (size - filled_count)
        return f"{self.paint(meter, self.CYAN)} {value}"

    def dashboard(self, tracks: Mapping[str, str], turn: Optional[int] = None, total: Optional[int] = None) -> None:
        if turn is not None and total is not None:
            progress = self.turn_progress(turn, total)
            print(f"  {self.badge(f'TURN {turn}/{total}', self.MAGENTA)} {progress}", file=self.stream)
        for key, value in tracks.items():
            label = key.replace("_", " ").title()
            print(f"  {label:<18} {self.track_meter(key, value)}", file=self.stream)

    def turn_progress(self, turn: int, total: int, width: int = 18) -> str:
        total = max(1, total)
        completed = max(0, min(total, turn))
        filled = round(completed / total * width)
        bar = "#" * filled + "." * (width - filled)
        if self.unicode:
            bar = "\u2588" * filled + "\u2591" * (width - filled)
        return self.paint(bar, self.CYAN)

    def risk_summary(self, risk: Mapping[str, str]) -> None:
        print(
            "  "
            + self.risk_badge(risk["overall"])
            + f"  likelihood={risk['likelihood']}  impact={risk['impact']}  confidence={risk['confidence']}",
            file=self.stream,
        )

    def choice(self, index: int, choice_id: str, label: str, description: str) -> None:
        number = self.badge(str(index), self.GREEN)
        cid = self.paint(choice_id, self.MAGENTA)
        print(f"\n  {number} {self.paint(label, self.BOLD)}  {self.muted(cid)}", file=self.stream)
        self.paragraph(description, indent=6)

    def change(self, label: str, before: str, after: str) -> None:
        arrow = "\u2192" if self.unicode else "->"
        print(f"  {self.paint('+', self.GREEN)} {label}: {before} {self.paint(arrow, self.CYAN)} {self.paint(after, self.BOLD)}", file=self.stream)

    def hint(self, text: str) -> None:
        print(f"\n  {self.muted('TIP')} {self.paint(text, self.DIM)}", file=self.stream)

    def success(self, text: str) -> None:
        print(self.paint(f"[OK] {text}", self.GREEN + self.BOLD), file=self.stream)

    def warning(self, text: str) -> None:
        print(self.paint(f"[!] {text}", self.YELLOW + self.BOLD), file=self.stream)

    def error(self, text: str) -> None:
        print(self.paint(f"[ERROR] {text}", self.RED + self.BOLD), file=self.stream)

    def prompt(self, turn: int, total: int) -> str:
        raw = f"matrix {turn + 1}/{total} > "
        return self.paint(raw, self.BOLD + self.CYAN)
