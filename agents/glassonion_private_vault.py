#!/usr/bin/env python3
"""Fail-closed local gate for Glass Onion private Zyra/Xunia material.

This module intentionally contains no private ontology data, recovery seed, passphrase,
TOTP secret, or device secret. The public repository may contain this gate; the secrets
and private data must remain local and outside Git.

`revealio` is an invocation word only. It is not treated as an authentication factor.
The private segment opens only after all three independent checks pass:

1. User-entered passphrase, verified against a SHA-256 digest stored in macOS Keychain.
2. User-entered TOTP code, verified with a base32 secret stored in macOS Keychain.
3. A separate device secret stored in macOS Keychain.

A local encrypted recovery-seed file is also mandatory. If it is missing, unreadable,
or has unsafe permissions, activation fails closed for the private Zyra/Xunia segment.
The rest of GPT-Doug/ZYRA is not terminated by this module.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import os
import platform
import stat
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

PRIVATE_ROOT = Path("intel/glassonion/private")
RECOVERY_SEED = PRIVATE_ROOT / "recovery.seed.enc"
PRIVATE_ONTOLOGY = PRIVATE_ROOT / "garnet_pommel_ontology.yaml.enc"

PASSPHRASE_HASH_SERVICE = "gpt-doug-glassonion-passphrase-sha256"
TOTP_SECRET_SERVICE = "gpt-doug-glassonion-totp"
DEVICE_SECRET_SERVICE = "gpt-doug-glassonion-device"


class PrivateVaultError(RuntimeError):
    """Raised when private-vault activation must fail closed."""


@dataclass(frozen=True, slots=True)
class PrivateVaultSession:
    authorized: bool
    scope: tuple[str, ...]
    ontology_path: Path


def _abort(reason: str) -> PrivateVaultError:
    return PrivateVaultError(f"ABORT_PRIVATE_ZYRA_XUNIA: {reason}")


def _keychain_account() -> str:
    return os.environ.get("GLASSONION_KEYCHAIN_ACCOUNT") or getpass.getuser()


def _keychain_read(service: str) -> str:
    if platform.system() != "Darwin":
        raise _abort("macOS Keychain is required for private-vault activation")
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                service,
                "-a",
                _keychain_account(),
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise _abort(f"required Keychain factor unavailable: {service}") from exc
    value = result.stdout.strip()
    if not value:
        raise _abort(f"required Keychain factor empty: {service}")
    return value


def _require_private_file(root: Path, relative: Path, *, min_size: int = 32) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise _abort("private path escaped repository root") from exc
    try:
        info = path.stat()
    except OSError as exc:
        raise _abort(f"required private artifact missing: {relative.as_posix()}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise _abort(f"private artifact is not a regular file: {relative.as_posix()}")
    if info.st_size < min_size:
        raise _abort(f"private artifact is unexpectedly small: {relative.as_posix()}")
    if info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise _abort(f"private artifact permissions must be owner-only: {relative.as_posix()}")
    return path


def _verify_passphrase(passphrase: str) -> None:
    expected = _keychain_read(PASSPHRASE_HASH_SERVICE).lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise _abort("stored passphrase digest is invalid")
    actual = hashlib.sha256(passphrase.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise _abort("passphrase verification failed")


def _totp(secret_b32: str, counter: int, digits: int = 6) -> str:
    normalized = "".join(secret_b32.strip().split()).upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        key = base64.b32decode(normalized + padding, casefold=True)
    except Exception as exc:  # binascii.Error varies by Python version
        raise _abort("stored TOTP secret is invalid") from exc
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10**digits)).zfill(digits)


def _verify_totp(code: str, *, now: int | None = None) -> None:
    clean = code.strip()
    if len(clean) != 6 or not clean.isdigit():
        raise _abort("TOTP code must be six digits")
    secret = _keychain_read(TOTP_SECRET_SERVICE)
    timestamp = int(time.time() if now is None else now)
    counter = timestamp // 30
    valid = any(hmac.compare_digest(clean, _totp(secret, counter + drift)) for drift in (-1, 0, 1))
    if not valid:
        raise _abort("TOTP verification failed")


def _verify_device_factor() -> None:
    secret = _keychain_read(DEVICE_SECRET_SERVICE)
    if len(secret.encode("utf-8")) < 32:
        raise _abort("device factor is too short")


def authorize_private_vault(
    root: str | Path,
    *,
    passphrase: str,
    totp_code: str,
) -> PrivateVaultSession:
    """Authorize only the private Zyra/Xunia segment, failing closed on any gap."""
    root_path = Path(root).resolve()
    _require_private_file(root_path, RECOVERY_SEED)
    ontology = _require_private_file(root_path, PRIVATE_ONTOLOGY)
    _verify_passphrase(passphrase)
    _verify_totp(totp_code)
    _verify_device_factor()
    return PrivateVaultSession(
        authorized=True,
        scope=("zyra_private", "xunia_private", "glassonion_private"),
        ontology_path=ontology,
    )


def status(root: str | Path) -> str:
    root_path = Path(root).resolve()
    try:
        _require_private_file(root_path, RECOVERY_SEED)
        _require_private_file(root_path, PRIVATE_ONTOLOGY)
    except PrivateVaultError as exc:
        return f"GLASSONION PRIVATE // SEALED // {exc}"
    return "GLASSONION PRIVATE // SEALED // local encrypted seed and ontology present"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed Glass Onion private-vault gate")
    parser.add_argument("action", choices=["revealio", "status"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    if args.action == "status":
        print(status(args.root))
        return 0

    passphrase = getpass.getpass("Glass Onion passphrase: ")
    totp_code = getpass.getpass("Authenticator code: ")
    try:
        session = authorize_private_vault(args.root, passphrase=passphrase, totp_code=totp_code)
    except PrivateVaultError as exc:
        print(str(exc))
        return 42

    print("GLASSONION PRIVATE // AUTHORIZED")
    print("Scope: " + ", ".join(session.scope))
    print("Private ontology remains local and encrypted at rest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
