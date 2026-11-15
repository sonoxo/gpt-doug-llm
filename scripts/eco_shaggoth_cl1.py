#!/usr/bin/env python3
"""ECO-SHAGGOTH-CL1: interactive spatial ecosystem for a real terminal.

Free, standard-library-only curses renderer. Read-only topology, live loopback
TCP probes (not authentication or service identity), no credential access,
commands, cloud calls, bank connections, background agents, or billing.
"""
from __future__ import annotations

import argparse
import curses
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
from dataclasses import dataclass, field

try:
    from scripts.cl1_aura_mouse import (
        footer_targets, hit_test, try_read_sgr_mouse, click_mask,
    )
except ModuleNotFoundError:
    # Direct invocation as "python3 scripts/eco_shaggoth_cl1.py".
    from cl1_aura_mouse import footer_targets, hit_test, try_read_sgr_mouse, click_mask

VERSION = "2026.11.14-aura-click.1"
ROOT = Path(__file__).resolve().parents[1]
LOCAL_PORTS = {"ollama": 11434, "cl1": 8787, "jukebox": 8844, "nexus": 8791}
LAYERS = ("ALL", "CORE", "DEFENSE", "INTELLIGENCE", "MUSIC", "FINANCE", "INFRA")
COLOR = {"green": 1, "cyan": 2, "violet": 3, "gold": 4, "red": 5, "dim": 6, "white": 7}


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    short: str
    layer: str
    xyz: tuple[float, float, float]
    kind: str
    details: str
    source: str = ""
    color: str = "cyan"


NODES = (
    Node("shaggoth", "ECO-SHAGGOTH", "SHAGGOTH", "CORE", (0, 0, 0),
         "architectural core", "Visual ecosystem center; a topology view, not a live AI agent.",
         "gpt_zyra_shaggoth/", "green"),
    Node("cl1", "GPT-DOUG CL1", "CL1 CORE", "CORE", (0, -2.8, -0.4),
         "local interface", "Local XUNIA web server; TCP listening is not a login check.",
         "web/xunia_server.py", "green"),
    Node("ollama", "OLLAMA INFERENCE", "OLLAMA", "CORE", (-4.2, -1.8, 0.7),
         "local inference", "Ollama model engine: local-only model admission, no cloud model fallback.",
         "agents/cl1_runtime_v2.py", "cyan"),
    Node("xunia", "XUNIA ORCHESTRATOR", "XUNIA", "CORE", (-3.5, 2.2, -0.4),
         "chat / streaming", "XUNIA routing, response streaming and the existing monitor.",
         "web/xunia_server.py", "cyan"),
    Node("kraken", "KRAKEN SHIELD", "KRAKEN", "DEFENSE", (3.2, 2.4, 0.8),
         "local guard", "Read-only decisions; emergency stop, input preflight and audit.",
         "kraken_shield/core.py", "violet"),
    Node("glass", "GLASS ONION", "GLASS ONION", "DEFENSE", (5.7, -1.0, -0.6),
         "service boundary", "Public music-link policy; banking operations default-deny.",
         "kraken_shield/service_policy.py", "violet"),
    Node("zyra", "ZYRA / GOLDEN SHIELD", "ZYRA", "DEFENSE", (-0.1, 3.7, 0.5),
         "policy engine", "Defensive inspection and approval boundary; no autonomous execution.",
         "golden_shield.py", "violet"),
    Node("redpanda", "RED PANDA", "RED PANDA", "INTELLIGENCE", (-6.7, 1.0, 0.7),
         "review division", "Repo intelligence / review track. Topology only; no live process assumed.",
         "gpt-redpanda-llm/", "gold"),
    Node("swarm", "SWARM / FLEET", "SWARM", "INTELLIGENCE", (-5.2, 4.3, 0),
         "agent orchestration", "Bounded agent coordination in the repository, not unlimited agents.",
         "gpt_zyra_shaggoth/factory.py", "gold"),
    Node("northstar", "NORTH STAR", "NORTH STAR", "INTELLIGENCE", (0.6, 5.5, -0.4),
         "strategy", "Strategic and ontology reference track; configuration is not execution.",
         "docs/", "gold"),
    Node("jukebox", "ZYRA JUKEBOX", "JUKEBOX", "MUSIC", (7.3, -3.0, 0.6),
         "music frontend", "Static music UI guarded for supported link / playback paths only.",
         "apps/zyra-jukebox/", "cyan"),
    Node("bank", "BANK POLICY", "BANK DENY", "FINANCE", (8.4, 0.8, 0.9),
         "restricted integration", "No connected bank adapter. Transfers and account reads are blocked.",
         "kraken_shield/service_policy.py", "red"),
    Node("vault", "PRIVATE VAULT", "VAULT", "FINANCE", (7.6, -5.0, 0.0),
         "sealed secrets", "The existing Glass Onion vault remains sealed, never inspected here.",
         "agents/glassonion_private_vault.py", "violet"),
    Node("nxyz", "NXYZ CLOUD", "NXYZ", "INFRA", (-7.0, -3.3, 0.2),
         "local/cloud project", "Repo-defined NXYZ project; this display does not provision a cloud.",
         "cloud_nxyz/", "cyan"),
    Node("greenhouse", "THE GREENHOUSE", "GREENHOUSE", "DEFENSE", (-8.1, 2.8, 0.7),
         "containment", "Fail-closed sandbox and governance concept, not a verified active service.",
         "governance/", "green"),
    Node("nexus", "SHAGGOTH NEXUS", "NEXUS", "INFRA", (-1.7, -5.4, 1.0),
         "local optional UI", "Optional defensive Nexus service; checks loopback TCP at 8791.",
         "gpt_zyra_shaggoth/nexus.py", "cyan"),
    Node("audit", "POLICY AUDIT", "AUDIT", "DEFENSE", (3.0, -5.2, 0.6),
         "local audit log", "Hash-linked local decisions: not externally anchored or tamper-proof.",
         "kraken_shield/core.py", "green"),
    Node("palantir", "FOUNDRY ADAPTER", "FOUNDRY", "INFRA", (4.1, 5.1, 0.2),
         "optional adapter", "Optional entitlement-dependent connector; not verified or activated.",
         "foundry/", "gold"),
)
BY_ID = {node.id: node for node in NODES}

# Labeled relationships: architectural intent, not live connection assertions.
EDGES = (
    ("shaggoth", "cl1", "contains"),
    ("shaggoth", "xunia", "orchestrates"),
    ("shaggoth", "kraken", "governed-by"),
    ("cl1", "ollama", "local-model"),
    ("cl1", "xunia", "interface"),
    ("xunia", "zyra", "review"),
    ("kraken", "zyra", "policy"),
    ("kraken", "glass", "service-gate"),
    ("kraken", "audit", "audit"),
    ("glass", "jukebox", "music-policy"),
    ("glass", "bank", "default-deny"),
    ("glass", "vault", "sealed"),
    ("zyra", "greenhouse", "containment"),
    ("xunia", "swarm", "bounded-coordination"),
    ("swarm", "redpanda", "review"),
    ("swarm", "northstar", "strategy"),
    ("xunia", "nexus", "optional-view"),
    ("cl1", "nxyz", "project"),
    ("northstar", "palantir", "optional-adapter"),
)
assert len(BY_ID) == len(NODES)
assert all(a in BY_ID and b in BY_ID for a, b, _ in EDGES)


def probe_local(port: int, timeout: float = 0.10) -> str:
    """Only inspect loopback TCP: cannot certify an application or its security."""
    if type(port) is not int or not 1 <= port <= 65535:
        return "UNKNOWN"
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return "LISTENING"
    except OSError:
        return "OFFLINE"


def health_snapshot(offline: bool = False) -> dict[str, str]:
    health = {}
    for node in NODES:
        if node.id in LOCAL_PORTS:
            health[node.id] = "UNTESTED" if offline else probe_local(LOCAL_PORTS[node.id])
        elif node.id == "bank":
            health[node.id] = "DENY"
        elif node.id == "vault":
            health[node.id] = "SEALED"
        elif node.id in ("kraken", "glass"):
            health[node.id] = "CODE" if (ROOT / node.source).is_file() else "MISSING"
        else:
            health[node.id] = "MAPPED"
    return health


def topology() -> dict:
    return {
        "schema": "eco-shaggoth/cl1-spatial-v1",
        "version": VERSION,
        "mode": "read-only-terminal-topology",
        "live_checks": "loopback_TCP_only_not_identity_verification",
        "external_calls": False,
        "bank_accounts_connected": False,
        "bank_transactions_enabled": False,
        "vault_unlocked": False,
        "nodes": [
            {"id": n.id, "name": n.name, "short": n.short,
             "layer": n.layer, "xyz": list(n.xyz),
             "kind": n.kind, "details": n.details,
             "source": n.source, "color": n.color}
            for n in NODES
        ],
        "edges": [{"source": a, "target": b, "relation": rel}
                  for a, b, rel in EDGES],
    }


def rotate_project(xyz: tuple[float, float, float], yaw: float, pitch: float,
                   zoom: float, width: int, height: int,
                   pan_x: float = 0, pan_y: float = 0) -> tuple[int, int, float]:
    """Perspective-lite projection of grounded 3D node coordinates."""
    x, y, z = xyz
    xx = x * math.cos(yaw) - z * math.sin(yaw)
    zz = x * math.sin(yaw) + z * math.cos(yaw)
    yy = y * math.cos(pitch) - zz * math.sin(pitch)
    depth = y * math.sin(pitch) + zz * math.cos(pitch)
    perspective = 1.0 / max(0.65, 1 + depth * 0.025)
    sx = round(width / 2 + pan_x + xx * 2.6 * zoom * perspective)
    sy = round(height / 2 + pan_y - yy * 1.45 * zoom * perspective)
    return sx, sy, depth


class Canvas:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.cells = [[(" ", COLOR["dim"]) for _ in range(width)]
                      for _ in range(height)]

    def put(self, x: int, y: int, char: str, color: int = 6) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = (char[:1] or " ", color)

    def text(self, x: int, y: int, content: str, color: int = 2) -> None:
        for step, ch in enumerate(content):
            self.put(x + step, y, ch, color)

    def line(self, x0: int, y0: int, x1: int, y1: int,
             color: int = 6, char: str = "·") -> None:
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        step_x = 1 if x0 < x1 else -1
        step_y = 1 if y0 < y1 else -1
        err = dx - dy
        for _ in range(min(2000, dx + dy + 2)):
            self.put(x0, y0, char, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += step_x
            if e2 < dx:
                err += dx
                y0 += step_y


@dataclass
class View:
    yaw: float = 0.12
    pitch: float = 0.26
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    selected: str = "shaggoth"
    layer: str = "ALL"
    labels: bool = True
    grid: bool = True
    animated: bool = True
    help: bool = False
    running: bool = True
    notice: str = "Spatial topology loaded. Runtime status is independently probed."
    tick: int = 0
    coords: dict[str, tuple[int, int]] = field(default_factory=dict)
    aura_drag: tuple[int, int] | None = None
    aura_last_click: tuple[int, int, float] | None = None
    aura_rescan: bool = False
    aura_events: int = 0


def visible_nodes(view: View) -> tuple[Node, ...]:
    return tuple(n for n in NODES if view.layer == "ALL" or n.layer == view.layer)


def draw_world(canvas: Canvas, view: View) -> dict[str, tuple[int, int]]:
    w, h = canvas.width, canvas.height
    if view.grid:
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if ((x * 7 + y * 13) % 67 == 0):
                    canvas.put(x, y, "·", COLOR["dim"])
    current = {node.id: rotate_project(
        node.xyz, view.yaw, view.pitch, view.zoom, w, h, view.pan_x, view.pan_y
    ) for node in visible_nodes(view)}
    for a, b, _ in EDGES:
        if a in current and b in current:
            ax, ay, _ = current[a]
            bx, by, _ = current[b]
            canvas.line(ax, ay, bx, by, COLOR["dim"], "·")
            if view.animated:
                progress = (view.tick % 30) / 30.0
                ex = round(ax + (bx - ax) * progress)
                ey = round(ay + (by - ay) * progress)
                canvas.put(ex, ey, "◆", COLOR["green"])
    selected = view.selected
    # An organic, breathing ASCII morphology centered on the actual core node.
    if "shaggoth" in current and view.animated:
        cx, cy, _ = current["shaggoth"]
        for arm in range(7):
            phase = arm * math.tau / 7
            for step in range(5, 13):
                t = step / 3.1
                x = round(cx + (t * math.cos(phase + 0.13 * math.sin(view.tick / 7 + step))))
                y = round(cy + (t * 0.53 * math.sin(phase + 0.18 * math.cos(view.tick / 9 + step))))
                canvas.put(x, y, "∿", COLOR["green"] if arm % 2 else COLOR["violet"])
    for node in sorted(visible_nodes(view), key=lambda n: current[n.id][2], reverse=True):
        x, y, _ = current[node.id]
        chosen = node.id == selected
        color = COLOR["white"] if chosen else COLOR[node.color]
        canvas.put(x, y, "◉" if chosen else "●", color)
        if view.labels:
            label = " " + node.short + (" ◀" if chosen else "")
            canvas.text(x + 2, y, label[:18], color)
    return {nid: (p[0], p[1]) for nid, p in current.items()}


def snapshot_text(width: int = 120, height: int = 30, offline: bool = False) -> str:
    width, height = max(60, width), max(16, height)
    view = View(animated=False)
    canvas = Canvas(width, height)
    draw_world(canvas, view)
    health = health_snapshot(offline=offline)
    headline = "ECO-SHAGGOTH-CL1  |  SPATIAL ECOSYSTEM  |  READ ONLY / FREE ONLY"
    lines = [headline, "=" * min(width, len(headline))]
    lines.extend("".join(cell[0] for cell in row).rstrip()
                 for row in canvas.cells)
    lines.extend((
        "",
        "LOCAL STATUS: " + "   ".join(
            f"{BY_ID[nid].short}:{health[nid]}"
            for nid in ("ollama", "cl1", "jukebox", "nexus", "bank", "vault")
        ),
        "INTERACTIVE: python3 scripts/eco_shaggoth_cl1.py",
        "STATUS NOTE: LISTENING means TCP reachable only; MAPPED/CODE is not online.",
    ))
    return "\n".join(lines)


def _safe_add(screen, y: int, x: int, content: str, color: int = 7,
              bold: bool = False, max_x: int | None = None) -> None:
    h, w = screen.getmaxyx()
    limit = min(max_x if max_x is not None else w - 1, w - 1)
    if y < 0 or y >= h or x < 0 or x >= limit:
        return
    text = content[:max(0, limit - x)]
    if not text:
        return
    attr = curses.color_pair(color) | (curses.A_BOLD if bold else 0)
    try:
        screen.addstr(y, x, text, attr)
    except (curses.error, UnicodeError):
        pass


def _box(screen, top: int, left: int, bottom: int, right: int,
         label: str, color: int = 2) -> None:
    if right - left < 5 or bottom - top < 3:
        return
    _safe_add(screen, top, left, "╭" + "─" * (right - left - 1) + "╮", color)
    _safe_add(screen, bottom, left, "╰" + "─" * (right - left - 1) + "╯", color)
    for y in range(top + 1, bottom):
        _safe_add(screen, y, left, "│", color)
        _safe_add(screen, y, right, "│", color)
    _safe_add(screen, top, left + 2, " " + label[:max(0, right-left-7)] + " ", color, True)


def _line_canvas(screen, canvas: Canvas, ox: int, oy: int) -> None:
    for y, row in enumerate(canvas.cells):
        if not row:
            continue
        start = 0
        while start < len(row):
            color = row[start][1]
            end = start + 1
            while end < len(row) and row[end][1] == color:
                end += 1
            _safe_add(screen, oy+y, ox+start,
                      "".join(cell[0] for cell in row[start:end]), color)
            start = end


def _status_color(value: str) -> int:
    if value == "LISTENING":
        return COLOR["green"]
    if value in ("SEALED", "DENY"):
        return COLOR["violet"]
    if value in ("OFFLINE", "MISSING"):
        return COLOR["red"]
    return COLOR["gold"]


def _render(screen, view: View, health: dict[str, str]) -> None:
    screen.erase()
    h, w = screen.getmaxyx()
    if w < 89 or h < 23:
        _safe_add(screen, 1, 2, "ECO-SHAGGOTH / CL1 - enlarge terminal to 89x23", 2, True)
        _safe_add(screen, 3, 2, f"Current size: {w}x{h} | Q quits", 4)
        screen.refresh()
        return
    left_width = 24
    right_width = 31
    mid_left = left_width + 1
    mid_right = w - right_width - 2
    mid_top, mid_bottom = 4, h - 5
    canvas = Canvas(mid_right - mid_left - 1, mid_bottom - mid_top - 1)
    view.coords = draw_world(canvas, view)
    _safe_add(screen, 0, 2, "✧ CL1-AURA // ECO-SHAGGOTH CLICKABLE SPATIAL TERMINAL", 1, True)
    _safe_add(screen, 1, 2, "MOUSE: CLICK NODES / LAYERS / LINKS  ◈  CL1 / XUNIA / KRAKEN / GLASS ONION", 2)
    _safe_add(screen, 2, 2, "TOPOLOGY ≠ PROCESS STATUS  |  TCP LISTENING ≠ AUTHENTICATED", 4)
    _box(screen, 4, 0, h-5, left_width, "ECOSYSTEM", 1)
    _box(screen, mid_top, mid_left, mid_bottom, mid_right, "SPATIAL ECO // XYZ", 2)
    _box(screen, 4, w-right_width-1, h-5, w-2, "NODE INSPECTOR", 3)
    _line_canvas(screen, canvas, mid_left + 1, mid_top + 1)
    _safe_add(screen, 5, 2, "LAYERS", 2, True)
    for i, layer in enumerate(LAYERS):
        _safe_add(screen, 7+i, 2, (">" if view.layer == layer else " ") +
                  " " + layer, 1 if view.layer == layer else 6,
                  view.layer == layer)
    _safe_add(screen, 16, 2, "LOCAL TELEMETRY", 2, True)
    for i, nid in enumerate(("ollama", "cl1", "jukebox", "nexus")):
        value = health.get(nid, "UNTESTED")
        _safe_add(screen, 18+i, 2, BY_ID[nid].short[:9], 7)
        _safe_add(screen, 18+i, 12, value[:10], _status_color(value), True)
    rx = w-right_width+1
    sel = BY_ID[view.selected]
    details_width = max(13, right_width - 7)
    _safe_add(screen, 6, rx, sel.name[:details_width], 1, True)
    _safe_add(screen, 8, rx, "CATEGORY: " + sel.layer, 2)
    _safe_add(screen, 9, rx, "TYPE: " + sel.kind[:details_width-7], 7)
    _safe_add(screen, 10, rx, "STATE: " + health.get(sel.id, "UNTESTED"),
              _status_color(health.get(sel.id, "UNTESTED")), True)
    _safe_add(screen, 12, rx, "DESCRIPTION", 2, True)
    maxw = right_width - 6
    import textwrap
    for i, line in enumerate(textwrap.wrap(sel.details, width=maxw)[:5]):
        _safe_add(screen, 13+i, rx, line, 7)
    _safe_add(screen, 19, rx, "SOURCE (REPO)", 2, True)
    for i, line in enumerate(textwrap.wrap(sel.source or "-", width=maxw)[:3]):
        _safe_add(screen, 20+i, rx, line, 6)
    if h >= 34:
        _safe_add(screen, 24, rx, "LINKS", 2, True)
        connections = [
            (b if a == sel.id else a, rel)
            for a, b, rel in EDGES if a == sel.id or b == sel.id
        ][:max(1, h-31)]
        for i, (nid, relation) in enumerate(connections):
            _safe_add(screen, 25+i, rx, f"• {BY_ID[nid].short[:12]} / {relation[:10]}", 6)
    footer_y = h-4
    _safe_add(screen, footer_y, 2,
              f"SELECT [{sel.id}]  ROTATE {math.degrees(view.yaw)%360:.0f}° "
              f"TILT {math.degrees(view.pitch):+.0f}°  ZOOM {view.zoom:.2f}× "
              f"LAYER {view.layer}", 4)
    for left, _, label, _ in footer_targets():
        _safe_add(screen, h-3, left, label, 1, True)
    _safe_add(screen, h-2, 2,
              "CLICK NODES / INSPECTOR / LAYERS  |  DRAG ROTATE  |  TAB / ARROWS  |  Q QUIT", 2)
    # Keep the notice in the top strip instead of obscuring clickable actions.
    _safe_add(screen, 3, 2, "AURA: " + view.notice[:max(0, w-15)], 4)
    if view.help:
        top = max(3, h//2-5)
        right = min(w-4, w//2+39)
        left = max(3, w//2-39)
        bottom = min(h-6, top+11)
        _box(screen, top, left, bottom, right, "INTERACTIVE CONTROLS", 4)
        tips = (
            "ARROWS: orbit 3D camera     H/J/K/L: pan field",
            "+ / - : zoom                TAB / SHIFT TAB: select node",
            "ENTER: focus selected       N / B: cycle layer filters",
            "/ : search nodes           R: rescan loopback TCP",
            "F: reset view              G: toggle star grid",
            "V: animated tentacles      L: node labels",
            "MOUSE: click nodes, layers, linked entities, footer",
            "DRAG: orbit view           WHEEL: zoom",
            "?: close help              Q: quit safely",
        )
        for i, tip in enumerate(tips):
            _safe_add(screen, top+2+i, left+2, tip, 7, max_x=right-1)
    screen.refresh()


def _find_node(search: str) -> str | None:
    search = search.lower().strip()
    return next((n.id for n in NODES
                 if search in (n.id, n.name.lower(), n.short.lower())
                 or search in n.name.lower()), None) if search else None


def _step_selection(view: View, delta: int) -> None:
    names = [n.id for n in visible_nodes(view)]
    if not names:
        return
    index = names.index(view.selected) if view.selected in names else -1
    view.selected = names[(index + delta) % len(names)]


def _aura_apply_hit(view: View, hit) -> None:
    """Change visible UI state only: no commands or repository mutations."""
    action = hit.action
    if action == "node":
        if hit.target not in BY_ID:
            return
        view.selected = hit.target
        if BY_ID[hit.target].layer != view.layer and view.layer != "ALL":
            view.layer = "ALL"
        view.notice = "INSPECT " + BY_ID[hit.target].name
    elif action == "layer":
        if hit.target not in LAYERS:
            return
        view.layer = hit.target
        if view.selected not in {n.id for n in visible_nodes(view)}:
            view.selected = visible_nodes(view)[0].id
        view.notice = "FILTER " + view.layer
    elif action == "scan":
        view.aura_rescan = True
        view.notice = "Refreshing localhost TCP only."
    elif action == "rotate_left":
        view.yaw -= 0.14
        view.notice = "Orbit left"
    elif action == "rotate_right":
        view.yaw += 0.14
        view.notice = "Orbit right"
    elif action == "zoom_in":
        view.zoom = min(3.0, view.zoom * 1.15)
        view.notice = "Zoom in"
    elif action == "zoom_out":
        view.zoom = max(0.40, view.zoom / 1.15)
        view.notice = "Zoom out"
    elif action == "help":
        view.help = not view.help
        view.notice = "AURA help"
    elif action == "reset":
        view.yaw, view.pitch, view.zoom = 0.12, 0.26, 1.0
        view.pan_x = view.pan_y = 0.0
        view.layer = "ALL"
        view.notice = "View reset"


def aura_mouse_event(
    view: View, mouse_x: int, mouse_y: int, button: int, screen,
    *, sgr: bool = False, pressed: bool = True,
) -> bool:
    """Handle native curses and raw SGR Mac mouse reports.

    Returns True if a user action changed the viewport or selection.
    """
    if sgr:
        if button & 64:
            view.zoom = min(3.0, view.zoom * 1.10) if (button & 1) == 0 else max(0.40, view.zoom / 1.10)
            view.aura_events += 1
            view.notice = "AURA scroll zoom"
            return True
        if button & 32:
            moving = True
        else:
            moving = False
        if not pressed:
            view.aura_drag = None
            return False
        clicking = not moving and (button & 3) == 0
    else:
        if button & getattr(curses, "BUTTON4_PRESSED", 0):
            view.zoom = min(3.0, view.zoom * 1.10)
            view.aura_events += 1
            return True
        if button & getattr(curses, "BUTTON5_PRESSED", 0):
            view.zoom = max(0.40, view.zoom / 1.10)
            view.aura_events += 1
            return True
        moving = bool(button & getattr(curses, "REPORT_MOUSE_POSITION", 0))
        clicking = bool(button & click_mask(curses)) and bool(
            button & (
                getattr(curses, "BUTTON1_PRESSED", 0) |
                getattr(curses, "BUTTON1_CLICKED", 0) |
                getattr(curses, "BUTTON1_DOUBLE_CLICKED", 0)
            )
        )
        if button & getattr(curses, "BUTTON1_RELEASED", 0):
            view.aura_drag = None
            return False
    if moving and view.aura_drag is not None:
        dx = mouse_x - view.aura_drag[0]
        dy = mouse_y - view.aura_drag[1]
        if dx or dy:
            view.yaw += dx * 0.045
            view.pitch = max(-1.2, min(1.2, view.pitch - dy * 0.045))
            view.aura_drag = (mouse_x, mouse_y)
            view.aura_events += 1
            view.notice = "AURA drag orbit"
            return True
    if not clicking:
        return False
    # One physical press is sometimes reported twice (PRESSED and CLICKED).
    now = time.monotonic()
    if view.aura_last_click is not None:
        x0, y0, t0 = view.aura_last_click
        if (x0, y0) == (mouse_x, mouse_y) and now - t0 < 0.18:
            return False
    view.aura_last_click = (mouse_x, mouse_y, now)
    h, w = screen.getmaxyx()
    hit = hit_test(
        mouse_x, mouse_y, width=w, height=h, selected=view.selected,
        coords=view.coords, edges=EDGES, visible=visible_nodes(view), layers=LAYERS,
    )
    # Clicking empty canvas starts an orbit drag without selecting an entity.
    if 26 <= mouse_x < w - 33 and 5 <= mouse_y < h - 5:
        view.aura_drag = (mouse_x, mouse_y)
    if hit is None:
        return False
    _aura_apply_hit(view, hit)
    view.aura_events += 1
    return True


def _handle_key(view: View, key: int, screen) -> None:
    if key in (ord("q"), ord("Q")):
        view.running = False
    elif key in (curses.KEY_RIGHT, ord("d")):
        view.yaw += 0.12
    elif key in (curses.KEY_LEFT, ord("a")):
        view.yaw -= 0.12
    elif key in (curses.KEY_UP, ord("w")):
        view.pitch = min(1.2, view.pitch + 0.10)
    elif key in (curses.KEY_DOWN, ord("s")):
        view.pitch = max(-1.2, view.pitch - 0.10)
    elif key in (ord("h"),):
        view.pan_x += 3
    elif key in (ord("l"),):
        view.pan_x -= 3
    elif key in (ord("j"),):
        view.pan_y -= 2
    elif key in (ord("k"),):
        view.pan_y += 2
    elif key in (ord("+"), ord("=")):
        view.zoom = min(3.0, view.zoom * 1.14)
    elif key in (ord("-"), ord("_")):
        view.zoom = max(0.40, view.zoom / 1.14)
    elif key == 9:
        _step_selection(view, 1)
    elif key == curses.KEY_BTAB:
        _step_selection(view, -1)
    elif key in (10, 13, curses.KEY_ENTER):
        # Focus selected node in the current spatial rotation.
        h, w = screen.getmaxyx()
        canvas_w = max(20, w - 59)
        canvas_h = max(10, h - 11)
        x, y, _ = rotate_project(BY_ID[view.selected].xyz, view.yaw, view.pitch,
                                 view.zoom, canvas_w, canvas_h)
        view.pan_x = canvas_w//2 - x
        view.pan_y = canvas_h//2 - y
    elif key in (ord("n"), ord("b")):
        delta = 1 if key == ord("n") else -1
        view.layer = LAYERS[(LAYERS.index(view.layer) + delta) % len(LAYERS)]
        if view.selected not in [n.id for n in visible_nodes(view)]:
            view.selected = visible_nodes(view)[0].id
    elif key == ord("f"):
        defaults = View()
        view.yaw, view.pitch, view.zoom = defaults.yaw, defaults.pitch, defaults.zoom
        view.pan_x = view.pan_y = 0
        view.layer = "ALL"
    elif key == ord("g"):
        view.grid = not view.grid
    elif key == ord("v"):
        view.animated = not view.animated
    elif key == ord("t"):
        view.labels = not view.labels
    elif key == ord("?"):
        view.help = not view.help
    elif key == ord("/"):
        h, _ = screen.getmaxyx()
        curses.echo()
        try:
            curses.curs_set(1)
            _safe_add(screen, h-2, 2, "FIND NODE: " + " " * 42, 4)
            screen.move(h-2, 13)
            name = screen.getstr(h-2, 13, 36).decode("utf-8", "ignore")
            found = _find_node(name)
            if found:
                view.selected = found
                view.layer = "ALL"
                view.notice = "Focused " + BY_ID[found].name
            else:
                view.notice = "No matching node: " + name[:24]
        finally:
            curses.noecho()
            try:
                curses.curs_set(0)
            except curses.error:
                pass
    elif key == curses.KEY_MOUSE:
        try:
            _, x, y, _, button = curses.getmouse()
            aura_mouse_event(view, x, y, button, screen)
        except curses.error:
            pass
    elif key == 27:
        # Some macOS curses builds forward raw xterm SGR mouse sequences as ESC.
        report = try_read_sgr_mouse(screen)
        if report is not None:
            x, y, button, pressed = report
            aura_mouse_event(view, x, y, button, screen, sgr=True, pressed=pressed)
        else:
            view.running = False


def _init_colors() -> None:
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    colors = (
        curses.COLOR_GREEN, curses.COLOR_CYAN, curses.COLOR_MAGENTA,
        curses.COLOR_YELLOW, curses.COLOR_RED, curses.COLOR_BLUE,
        curses.COLOR_WHITE,
    )
    for idx, color in enumerate(colors, 1):
        curses.init_pair(idx, color, -1)


def run_curses(screen, offline: bool = False) -> None:
    screen.nodelay(True)
    screen.keypad(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    if curses.has_colors():
        _init_colors()
    try:
        curses.mouseinterval(0)
        mask = curses.ALL_MOUSE_EVENTS | getattr(curses, "REPORT_MOUSE_POSITION", 0)
        curses.mousemask(mask)
        # SGR-1006 coordinates work beyond the legacy 223-cell mouse limit.
        # Use button-event tracking; reset both modes on exit.
        sys.stdout.write("\x1b[?1006h\x1b[?1002h")
        sys.stdout.flush()
    except (curses.error, OSError):
        pass
    view = View()
    health = health_snapshot(offline=offline)
    last_probe = time.monotonic()
    last_frame = time.monotonic()
    while view.running:
        now = time.monotonic()
        if not offline and now - last_probe > 5.0:
            health = health_snapshot()
            last_probe = now
        _render(screen, view, health)
        key = screen.getch()
        if key == ord("r"):
            health = health_snapshot(offline=offline)
            view.notice = "Rescanned loopback endpoints; no external account checks."
            last_probe = now
        elif key != -1:
            _handle_key(view, key, screen)
        if view.aura_rescan:
            health = health_snapshot(offline=offline)
            last_probe = now
            view.aura_rescan = False
        if view.animated:
            view.tick += 1
        elapsed = time.monotonic() - last_frame
        time.sleep(max(0.02, 0.11 - elapsed))
        last_frame = time.monotonic()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ECO-SHAGGOTH-CL1 spatial terminal ecosystem")
    parser.add_argument("--snapshot", action="store_true",
                        help="Print spatial topology in plain terminal text")
    parser.add_argument("--json", action="store_true",
                        help="Print machine-readable architectural graph only")
    parser.add_argument("--offline", action="store_true",
                        help="Disable all loopback TCP probes")
    args = parser.parse_args(argv)
    if args.json:
        print(json.dumps(topology(), indent=2))
        return 0
    if args.snapshot or not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(snapshot_text(offline=args.offline))
        return 0
    try:
        curses.wrapper(lambda screen: run_curses(screen, offline=args.offline))
    except KeyboardInterrupt:
        pass
    finally:
        # Always restore the terminal's normal mouse/selection behavior.
        try:
            sys.stdout.write("\x1b[?1002l\x1b[?1006l")
            sys.stdout.flush()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
