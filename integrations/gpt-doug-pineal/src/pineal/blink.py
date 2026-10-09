"""Animated local Mac terminal 'blink': a visual symbolic cell heartbeat.

Does not collect EEG, grow cells, stimulate brains, or fetch patent data.
"""
from __future__ import annotations

import math
import os
import sys
import time
from datetime import datetime
from typing import TextIO

from .cells import list_cells
from .patent_connectors import patent_connection_status
from .store import PinealStore


def render_blink(store: PinealStore, *, frame: int = 0, color: bool = False) -> str:
    """Generate one read-only ANSI-compatible terminal snapshot."""
    on = frame % 2 == 0
    pulse = '●' if on else '○'
    neuron = '◉' if on else '◎'
    timeline = ('▁▂▅█▅▂▁' if on else '▁▃▆▇▆▃▁')
    stats = store.patent_stats()
    audit = store.verify_audit()
    sources = {row["id"]: row for row in patent_connection_status()}
    ops = "CONFIGURED" if sources["epo-ops"]["configured"] else "NEEDS KEY"
    pv = "CONFIGURED" if sources["patentsview-us"]["configured"] else "NEEDS KEY"
    now = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
    green = '\033[1;32m' if color else ''
    blue = '\033[1;36m' if color else ''
    reset = '\033[0m' if color else ''
    return '\n'.join([
        '=' * 82,
        f'{blue}  PINEAL // BLINK    {pulse}  CELLULAR CORTEX    // SHAGGOTH-KRAKEN{reset}',
        f'  {now}   |   LOCAL SYMBOLIC VISUALIZATION   |   FRAME {frame + 1}',
        '=' * 82,
        '',
        f'                 . - - - - - - - - - - .',
        f'               /                         \\',
        f'              |        {neuron}    DNA          |',
        f'              |     ~ cytoplasm ~        |',
        f'              |      mitochondria       |',
        f'               \\                       /',
        f'                 ` - - - - - - - - - - `',
        '',
        f'  BLINK        {green}{pulse} {timeline}{reset}     |   SOFTWARE HEARTBEAT: DEMONSTRATION',
        f'  CELL ATLAS   {len(list_cells())} curated educational human cell classes',
        f'  PATENT INDEX {stats["total"]} indexed LOCAL bibliographic records',
        f'  PROVENANCE   {green}{"AUDIT OK" if audit["ok"] else "AUDIT FAILED"}{reset}  /  {audit["checked"]} logged mutations',
        f'  PATENT FEEDS OPS: {ops}  |  PATENTSVIEW: {pv}  |  LIVE VERIFIED: 0',
        '  SOURCES      EPO EP public/OPS worldwide; US grants PV; WIPO/ODP: licensed exports',
        '  ACCESS       NO HUMAN BRAIN I/O  |  NO AUTONOMOUS EXTERNAL CONNECTIONS',
        '  REALITY      LIVING CELLS CREATED: NO  |  SYMBOLIC COMPUTER MODEL ONLY',
        '  EVIDENCE     PATENT DISCLOSURE DOES NOT ESTABLISH SCIENTIFIC VALIDITY',
        '',
        '  COMMANDS     pineal cells list   |   pineal patents sources',
        '  Stop live animation: Ctrl+C',
        '=' * 82,
        '',
    ])


def run_blink(store: PinealStore, *, watch: bool = False, interval: float = 0.6,
              frames: int | None = None, color: bool | None = None,
              stream: TextIO | None = None) -> int:
    if not isinstance(interval, (float, int)) or not math.isfinite(interval) or not 0 < interval <= 60:
        raise ValueError('blink interval must be finite and between 0 and 60 seconds')
    if frames is not None and (type(frames) is not int or not 1 <= frames <= 10000):
        raise ValueError('frames must be a positive integer <=10000')
    out = stream if stream is not None else sys.stdout
    tty = bool(getattr(out, 'isatty', lambda: False)())
    use_color = color if color is not None else tty and 'NO_COLOR' not in os.environ
    max_frames = frames if frames is not None else (None if watch else 1)
    counter = 0
    try:
        while max_frames is None or counter < max_frames:
            if tty and (watch or (frames is not None and frames > 1)):
                out.write('\033[H\033[2J')
            out.write(render_blink(store, frame=counter, color=use_color))
            out.flush()
            counter += 1
            if max_frames is not None and counter == max_frames:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        out.write('\n')
    return 0
