"""CL1-AURA mouse layer for the ECO-SHAGGOTH curses terminal.

Pure hit testing is separated from terminal events so Mac/iTerm coordinate
translation, node selection, layer buttons and controls can be tested offline.
No shell access, external connections, credentials, or privileged APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable

FOOTER_ACTIONS = (
    ("[< ROT]", "rotate_left"),
    ("[ROT >]", "rotate_right"),
    ("[- ZOOM]", "zoom_out"),
    ("[+ ZOOM]", "zoom_in"),
    ("[SCAN]", "scan"),
    ("[RESET]", "reset"),
    ("[HELP]", "help"),
)
_SGR = re.compile(r"^\x1b\[<(\d{1,3});(\d{1,5});(\d{1,5})([Mm])$")


@dataclass(frozen=True)
class AuraHit:
    action: str
    target: str = ""


def footer_targets(start_x: int = 2) -> tuple[tuple[int, int, str, str], ...]:
    out = []
    x = start_x
    for text, action in FOOTER_ACTIONS:
        out.append((x, x + len(text), text, action))
        x += len(text) + 1
    return tuple(out)


def hit_test(
    mouse_x: int,
    mouse_y: int,
    *,
    width: int,
    height: int,
    selected: str,
    coords: dict[str, tuple[int, int]],
    nodes: dict[str, Any],
    visible: Iterable[Any],
    layers: tuple[str, ...],
) -> AuraHit | None:
    """Map absolute zero-indexed curses mouse position to a visible control."""
    if width < 89 or height < 23:
        return None
    if not (0 <= mouse_x < width and 0 <= mouse_y < height):
        return None

    # Footer buttons have fixed hit boxes matching the drawn text.
    if mouse_y == height - 3:
        for left, right, _, action in footer_targets():
            if left <= mouse_x < right:
                return AuraHit(action)
    # Layer filter buttons: rows 7..13, columns 2..23.
    if 2 <= mouse_x < 24 and 7 <= mouse_y < 7 + len(layers):
        return AuraHit("layer", layers[mouse_y - 7])

    # Live telemetry panel: selecting a service is read-only.
    if 2 <= mouse_x < 24 and 18 <= mouse_y <= 21:
        return AuraHit("node", ("ollama", "cl1", "jukebox", "nexus")[mouse_y - 18])

    right_width = 31
    rx = width - right_width + 1
    if height >= 34 and rx <= mouse_x < width - 2 and 25 <= mouse_y < height - 6:
        neighbors = [
            (b if a == selected else a)
            for a, b, _ in getattr(nodes, "EDGES", ())
            if a == selected or b == selected
        ]
        pos = mouse_y - 25
        if pos < len(neighbors):
            return AuraHit("node", neighbors[pos])

    # Canvas coordinates are projected relative to its inner upper left.
    viewport_left = 26
    viewport_top = 5
    viewport_right = width - right_width - 2
    viewport_bottom = height - 5
    if not (
        viewport_left <= mouse_x < viewport_right
        and viewport_top <= mouse_y < viewport_bottom
    ):
        return None

    candidates = []
    for node in visible:
        if node.id not in coords:
            continue
        cx, cy = coords[node.id]
        sx, sy = viewport_left + cx, viewport_top + cy
        if mouse_y != sy:
            continue
        label_right = sx + 2 + 1 + min(18, len(node.short) + 3)
        if sx - 1 <= mouse_x <= label_right:
            # Pick the nearest marker when labels overlap.
            candidates.append((abs(mouse_x - sx), node.id))
    if candidates:
        return AuraHit("node", min(candidates)[1])
    return None


def parse_sgr_mouse(sequence: str) -> tuple[int, int, int, bool] | None:
    """Decode an xterm SGR mouse report, including 1-index to 0-index mapping."""
    match = _SGR.fullmatch(sequence)
    if not match:
        return None
    button, x, y = map(int, match.groups()[:3])
    if x <= 0 or y <= 0 or x > 9999 or y > 9999:
        return None
    return x - 1, y - 1, button, match.group(4) == "M"


def try_read_sgr_mouse(screen) -> tuple[int, int, int, bool] | None:
    """Parse bounded raw ESC [ <... reports if curses doesn't emit KEY_MOUSE.

    This fallback never reads arbitrary stdin or opens any device. It is only
    invoked after curses returns ESC and is deliberately nonblocking/bounded.
    """
    result = "\x1b"
    try:
        screen.timeout(25)
        for _ in range(28):
            key = screen.getch()
            if key < 0:
                break
            if key > 127:
                break
            result += chr(key)
            if result.startswith("\x1b[<") and result[-1] in ("m", "M"):
                break
            if not "\x1b[<".startswith(result) and not result.startswith("\x1b[<"):
                break
    except Exception:
        return None
    finally:
        try:
            screen.timeout(0)
        except Exception:
            pass
    return parse_sgr_mouse(result)


def click_mask(curses_module) -> int:
    """Support pressed, clicked, double-clicked, and scroll-wheel events."""
    names = (
        "BUTTON1_PRESSED", "BUTTON1_CLICKED", "BUTTON1_DOUBLE_CLICKED",
        "BUTTON4_PRESSED", "BUTTON5_PRESSED",
    )
    mask = 0
    for name in names:
        mask |= getattr(curses_module, name, 0)
    return mask
