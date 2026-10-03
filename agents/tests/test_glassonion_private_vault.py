from __future__ import annotations

import hashlib
import stat
from pathlib import Path

import pytest

from agents import glassonion_private_vault as vault


def _write_private(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_missing_recovery_seed_aborts_private_scope(tmp_path: Path) -> None:
    _write_private(tmp_path / vault.PRIVATE_ONTOLOGY, b"x" * 64)
    with pytest.raises(vault.PrivateVaultError, match="ABORT_PRIVATE_ZYRA_XUNIA"):
        vault.authorize_private_vault(tmp_path, passphrase="correct", totp_code="123456")


def test_missing_private_ontology_aborts_private_scope(tmp_path: Path) -> None:
    _write_private(tmp_path / vault.RECOVERY_SEED, b"x" * 64)
    with pytest.raises(vault.PrivateVaultError, match="ABORT_PRIVATE_ZYRA_XUNIA"):
        vault.authorize_private_vault(tmp_path, passphrase="correct", totp_code="123456")


def test_insecure_seed_permissions_abort(tmp_path: Path) -> None:
    seed = tmp_path / vault.RECOVERY_SEED
    _write_private(seed, b"x" * 64)
    seed.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    _write_private(tmp_path / vault.PRIVATE_ONTOLOGY, b"x" * 64)
    with pytest.raises(vault.PrivateVaultError, match="permissions must be owner-only"):
        vault.authorize_private_vault(tmp_path, passphrase="correct", totp_code="123456")


def test_three_factors_authorize_only_private_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_private(tmp_path / vault.RECOVERY_SEED, b"seed" * 16)
    _write_private(tmp_path / vault.PRIVATE_ONTOLOGY, b"ontology" * 8)

    passphrase = "correct horse battery staple"
    totp_secret = "JBSWY3DPEHPK3PXP"
    device_secret = "device-secret-" + ("x" * 32)
    values = {
        vault.PASSPHRASE_HASH_SERVICE: hashlib.sha256(passphrase.encode()).hexdigest(),
        vault.TOTP_SECRET_SERVICE: totp_secret,
        vault.DEVICE_SECRET_SERVICE: device_secret,
    }
    monkeypatch.setattr(vault, "_keychain_read", lambda service: values[service])
    now = 1_700_000_000
    code = vault._totp(totp_secret, now // 30)
    monkeypatch.setattr(vault.time, "time", lambda: now)

    session = vault.authorize_private_vault(tmp_path, passphrase=passphrase, totp_code=code)

    assert session.authorized is True
    assert session.scope == ("zyra_private", "xunia_private", "glassonion_private")
    assert session.ontology_path == (tmp_path / vault.PRIVATE_ONTOLOGY).resolve()


def test_wrong_passphrase_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_private(tmp_path / vault.RECOVERY_SEED, b"seed" * 16)
    _write_private(tmp_path / vault.PRIVATE_ONTOLOGY, b"ontology" * 8)
    monkeypatch.setattr(
        vault,
        "_keychain_read",
        lambda service: hashlib.sha256(b"right").hexdigest()
        if service == vault.PASSPHRASE_HASH_SERVICE
        else "unused",
    )
    with pytest.raises(vault.PrivateVaultError, match="passphrase verification failed"):
        vault.authorize_private_vault(tmp_path, passphrase="wrong", totp_code="123456")
