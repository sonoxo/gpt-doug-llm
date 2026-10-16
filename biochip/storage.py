"""Private local SQLite files; same-UID malicious processes are outside this boundary."""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import stat


def file_path(raw: str | Path) -> Path:
    if not isinstance(raw, (str, Path)):
        raise ValueError('database path must be text or a Path')
    text = str(raw)
    if not text or text == ':memory:' or '\0' in text or text.startswith('file:'):
        raise ValueError('a regular file-backed database path is required')
    candidate = Path(text).expanduser().absolute()
    # Resolve existing ancestor aliases (including macOS /var) but never the leaf.
    return candidate.parent.resolve() / candidate.name


def check_file(path: Path) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise PermissionError('refusing a symlink, hardlink or nonregular database file')
    if os.name == 'posix' and (info.st_uid != os.geteuid() or info.st_mode & 0o077):
        raise PermissionError('database must be owned by this user with mode 0600; review and chmod that file explicitly')
    return info


def reserve_file(path: Path) -> os.stat_result:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        return os.fstat(fd)
    finally:
        os.close(fd)


def prepare_file(raw: str | Path) -> Path:
    path = file_path(raw)
    try:
        reserve_file(path)
    except FileExistsError:
        pass
    check_file(path)
    return path


def private_directory(raw: Path, *, create: bool = True) -> Path:
    path = file_path(raw)
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or
            (os.name == 'posix' and (info.st_uid != os.geteuid() or info.st_mode & 0o077))):
        raise PermissionError('state directory must be owned by this user, nonsymlink, and mode 0700')
    return path


def connect_private(raw: str | Path, *, read_only: bool = False) -> sqlite3.Connection:
    path = file_path(raw)
    before = check_file(path)
    mode = 'ro' if read_only else 'rw'
    db = sqlite3.connect(path.as_uri() + '?mode=' + mode, uri=True,
                         timeout=10, isolation_level=None)
    try:
        after = check_file(path)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise PermissionError('database changed while opening')
        db.execute('PRAGMA busy_timeout=10000')
        db.execute('PRAGMA trusted_schema=OFF')
        if read_only:
            db.execute('PRAGMA query_only=ON')
        return db
    except BaseException:
        db.close()
        raise
