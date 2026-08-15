"""At-rest encryption for project files.

Uses Fernet (AES-128-CBC + HMAC-SHA256, from the `cryptography` package) with
a key generated once and stored owner-only at ~/.gpt-doug/projects.key. Every
file written through the API is encrypted before it touches disk; it's
decrypted transparently when served to the preview iframe or copied into an
ephemeral directory for real project execution (see runner.py). The key never
leaves this machine and isn't part of the git repo.
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

KEY_PATH = Path.home() / ".gpt-doug" / "projects.key"
MAGIC = b"DOUGENC1:"


def _load_or_create_key() -> bytes:
    KEY_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    KEY_PATH.chmod(0o600)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_bytes(data: bytes) -> bytes:
    return MAGIC + _fernet.encrypt(data)


def is_encrypted(data: bytes) -> bool:
    return data.startswith(MAGIC)


def decrypt_bytes(data: bytes) -> bytes:
    """Decrypts if encrypted; returns data unchanged otherwise (so files
    written before this feature existed still serve without error)."""
    if not is_encrypted(data):
        return data
    try:
        return _fernet.decrypt(data[len(MAGIC):])
    except InvalidToken as err:
        raise ValueError("file is encrypted with a different key") from err
