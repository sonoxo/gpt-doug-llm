"""Confined local-only synthetic MECHA file intake."""
from __future__ import annotations
import json
import os
import stat
from pathlib import Path
from typing import Any
from .contracts import validate_fixture


def _read_confined_json(file: Path, *, input_root: Path) -> Any:
    root=Path(input_root).expanduser()
    candidate=Path(file).expanduser()
    if root.is_symlink() or not root.is_dir() or '..' in candidate.parts:
        raise ValueError('untrusted input directory or traversal')
    try:
        resolved_root=root.resolve(strict=True)
        real=candidate.resolve(strict=True)
        if not real.is_relative_to(resolved_root):
            raise ValueError('input outside allowed root')
        cur=candidate
        while True:
            if cur.is_symlink():
                raise ValueError('symlink input or ancestor prohibited')
            if cur==cur.parent:
                break
            cur=cur.parent
        flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_CLOEXEC',0)
        fd=os.open(str(candidate), flags)
        with os.fdopen(fd,'rb') as source:
            info=os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size>65536:
                raise ValueError('input is not a regular <=64 KiB file')
            raw=source.read(65537)
        if len(raw)>65536:
            raise ValueError('input exceeds 64 KiB')
        return json.loads(raw.decode('utf-8'),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON '+x)))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('invalid or unsafe JSON fixture') from exc


def load_fixture(file: Path, *, input_root: Path) -> dict[str, Any]:
    return validate_fixture(_read_confined_json(file,input_root=input_root))
