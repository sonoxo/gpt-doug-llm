"""Local pseudonymous operator alias, explicitly not identity verification.

A callsign controls only how research output is labelled. This module never
changes ZYRA/PINEAL authority, permissions, or the human review workflow.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CALLSIGN_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{1,31}\Z')
PROFILE = 'operator-profile.json'


def _validate_callsign(callsign: Any) -> str:
    if not isinstance(callsign, str) or not CALLSIGN_RE.fullmatch(callsign):
        raise ValueError('invalid local callsign (2-32 ASCII letters, digits, - or _)')
    return callsign


def _target(workspace: Path) -> Path:
    root = Path(workspace).expanduser()
    if root.is_symlink():
        raise ValueError('symlink workspace prohibited')
    target = root / PROFILE
    if target.is_symlink():
        raise ValueError('symlink operator profile prohibited')
    return target


def read_operator(workspace: Path) -> dict[str, Any] | None:
    target = _target(workspace)
    if not target.exists():
        return None
    if not target.is_file() or target.stat().st_size > 4096:
        raise ValueError('invalid or oversized local operator profile')
    try:
        data = json.loads(target.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid operator profile') from exc
    if (not isinstance(data, dict) or data.get('schema_version') != '1.0.0'
            or data.get('authority') != 'RESEARCH_ONLY'
            or data.get('identity_source') != 'SELF_DECLARED'
            or data.get('source_system') != 'LOCAL_ONLY'
            or data.get('identity_verified') is not False
            or data.get('military_affiliation_verified') is not False
            or data.get('granted_permissions') != []):
        raise ValueError('operator profile cannot grant credentials or authority')
    _validate_callsign(data.get('callsign'))
    return data


def register_operator(workspace: Path, callsign: str) -> dict[str, Any]:
    label = _validate_callsign(callsign)
    target = _target(workspace)
    old = read_operator(workspace)
    if old is not None:
        if old['callsign'] != label:
            raise ValueError('different callsign is already registered in this local workspace')
        return old
    root = target.parent
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink():
        raise ValueError('symlink workspace prohibited')
    root.chmod(0o700)
    data = {
        'schema_version': '1.0.0',
        'callsign': label,
        'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'identity_source': 'SELF_DECLARED',
        'source_system': 'LOCAL_ONLY',
        'identity_verified': False,
        'military_affiliation_verified': False,
        'authority': 'RESEARCH_ONLY',
        'granted_permissions': [],
        'note': 'Pseudonym only; not an authenticated military or government credential.',
    }
    text = json.dumps(data, sort_keys=True, indent=2) + '\n'
    fd, temp_path = tempfile.mkstemp(prefix='.operator-', suffix='.tmp', dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        try:
            os.link(temp_path, target)
        except FileExistsError:
            other = read_operator(workspace)
            if other is None or other['callsign'] != label:
                raise ValueError('different callsign is already registered in this local workspace')
            return other
    finally:
        Path(temp_path).unlink(missing_ok=True)
    return data
