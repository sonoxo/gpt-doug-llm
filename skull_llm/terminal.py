"""Portable, ANSI-free ASCII visuals for the SKULL-LLM terminal.

Only 7-bit printable ASCII is emitted.  No terminal library or paid API is
needed. The dashboard consumes real local doctor() observations; network and
banner renders are explicitly static architecture illustrations.
"""
from __future__ import annotations

import shutil
from typing import Any


SKULL_ART = r'''
                 .-""""""""-.
               .'  _      _  '.
              /   / \    / \   \
             |   | O |  | O |   |
             |   |___|  |___|   |
             |        /\        |
             |     .-____-.     |
              \    |_|__|_|    /
               '.__._______.__.'
                   /_|__|_\
'''.strip("\n")

NETWORK_ART = r"""
                      [ USER / TERMINAL ]
                               |
                               v
                       +---------------+
                       |   SKULL-LLM   |
                       | ORCHESTRATOR  |
                       +---------------+
                        /      |      \
                       v       v       v
                +---------+ +------+ +---------+
                | ONTOLOGY| |MEMORY| | LOCAL   |
                |  GRAPH  | |STORE | | OLLAMA  |
                +---------+ +------+ +---------+
                       \       |      /
                        \      v     /
                         +-----------+
                         | REASONING |
                         | DRAFT     |
                         | CRITIC    |
                         | REVISE    |
                         +-----------+
                               |
                               v
                        [ FINAL OUTPUT ]
""".strip("\n")


def _ascii(value: Any, maximum: int = 200, preserve_space: bool = False) -> str:
    """Make status strings safe for terminal display (no escape injection)."""
    cleaned = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in str(value))
    return (cleaned if preserve_space else " ".join(cleaned.split()))[:maximum]


def _width(columns: int | None) -> int:
    if columns is None:
        columns = shutil.get_terminal_size((80, 24)).columns
    return max(42, min(int(columns), 100))


def _panel(title: str, lines: list[str], *, columns: int | None = None) -> str:
    width = _width(columns)
    inner = width - 4
    border = "+" + "-" * (width - 2) + "+"
    heading = " " + _ascii(title, inner)[:inner].ljust(inner) + " "
    body = [border, "|" + heading + "|", border]
    for line in lines:
        safe = _ascii(line, 1000, preserve_space=True)
        if not safe.strip():
            body.append("|" + " " * (width - 2) + "|")
            continue
        while safe:
            part, safe = safe[:inner], safe[inner:]
            body.append("| " + part.ljust(inner) + " |")
    body.append(border)
    return "\n".join(body)


def _skull_block(columns: int | None = None) -> list[str]:
    width = _width(columns) - 4
    raw = SKULL_ART.splitlines()
    return [line.strip().center(width) for line in raw]


def render_banner(columns: int | None = None) -> str:
    lines = _skull_block(columns)
    lines += ["", "NEURAL INTELLIGENCE / GPT-DOUG-LLM / XUNIA", "ASCII CONSOLE / LOCAL FIRST"]
    return _panel("SKULL-LLM :: SYSTEM BANNER", lines, columns=columns)


def render_network(columns: int | None = None) -> str:
    lines = [
        "REFERENCE TOPOLOGY - NOT LIVE TELEMETRY", "",
        *NETWORK_ART.splitlines(),
        "",
        "Inference: local Ollama | Memory: opt-in | No paid API required",
    ]
    return _panel("SKULL-LLM :: NEURAL NETWORK MAP", lines, columns=columns)


def _state_label(ok: bool, positive: str, negative: str) -> str:
    return positive if ok else negative


def render_dashboard(snapshot: dict[str, Any], columns: int | None = None) -> str:
    """Render observed readiness only. Never substitute made-up performance data."""
    state = snapshot.get("ollama") or {}
    if not isinstance(state, dict):
        state = {}
    stopped = bool(snapshot.get("stopped"))
    model = _ascii(state.get("model") or "not selected", 64)
    backend = _state_label(bool(state.get("configured")), "REACHABLE", "OFFLINE")
    available = _state_label(bool(state.get("model_available")), "FOUND", "MISSING")
    pytorch = _state_label(bool(snapshot.get("pytorch_installed")), "INSTALLED", "NOT INSTALLED")
    ready = bool(snapshot.get("ready_for_inference"))
    system = "STOPPED" if stopped else _state_label(ready, "READY", "NOT READY")
    detail = _ascii(state.get("message", "No model diagnostics"), 140)
    lines = _skull_block(columns) + [
        "",
        "CORE          : " + system,
        "PROVIDER      : OLLAMA / LOOPBACK ONLY",
        "OLLAMA        : " + backend,
        "MODEL         : " + model,
        "MODEL FILE    : " + available,
        "PYTORCH       : " + pytorch,
        "EMERGENCY STOP: " + _state_label(stopped, "ENGAGED", "CLEAR"),
        "TRAINED WEIGHTS: NOT PROVIDED BY THIS PACKAGE",
        "",
        "DETAIL        : " + detail,
        "",
        "[ ONTOLOGY ] -- [ MEMORY ] -- [ LOCAL LLM ] -- [ CRITIC ]",
        "                  SKULL-LLM COMMAND DECK",
        "",
        "STATUS VALUES ARE OBSERVED, NOT BENCHMARK SCORES.",
    ]
    return _panel("SKULL-LLM :: LIVE LOCAL STATUS SNAPSHOT", lines, columns=columns)
