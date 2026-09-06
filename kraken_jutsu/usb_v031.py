from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class USBLayout:
    mount: Path
    runtime: Path
    state: Path


def install_usb(source_root: str | Path, mount: str | Path) -> USBLayout:
    mount = Path(mount).expanduser().resolve()
    if not mount.exists() or not os.access(mount, os.W_OK):
        raise PermissionError(f"USB mount unavailable or not writable: {mount}")
    runtime = mount / "KRAKENXYZ"
    state = mount / ".krakenxyz"
    app = runtime / "app"
    runtime.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    if app.exists():
        shutil.rmtree(app)
    shutil.copytree(
        Path(source_root).resolve(),
        app,
        ignore=shutil.ignore_patterns(
            ".git", ".venv", "build", "dist", "__pycache__", ".pytest_cache"
        ),
    )
    for rel in ("agent-inbox", "quarantine", "BLACKHOUSE/friends"):
        (state / rel).mkdir(parents=True, exist_ok=True)
    launcher = runtime / "kraken-jutsu"
    launcher.write_text(
        "#!/bin/sh\n"
        "set -eu\n"
        f'export KRAKENXYZ_STATE="{state}"\n'
        f'export PYTHONPATH="{app}${{PYTHONPATH:+:$PYTHONPATH}}"\n'
        'exec python3 -m kraken_jutsu.live "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return USBLayout(mount=mount, runtime=runtime, state=state)
