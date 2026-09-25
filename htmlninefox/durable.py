"""Crash-safe file primitives shared by every Project writer.

`atomic_write` is the single durable write primitive: same-directory temporary
file, fsync, atomic replace, and best-effort directory fsync on POSIX.

`acquire_file_lock` / `release_file_lock` provide a cross-process advisory
lock (msvcrt on Windows, fcntl elsewhere) with a bounded acquisition timeout.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:
    import fcntl

LOCK_RETRY_INTERVAL = 0.05
REPLACE_ATTEMPTS = 8


class LockBusyError(Exception):
    """The project file lock could not be acquired within the timeout."""


def atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".revision-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(temporary, path)
        _fsync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _replace_with_retry(temporary: str, path: Path) -> None:
    """os.replace can hit a transient sharing violation on Windows when
    another writer replaces the same destination concurrently."""
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(0.02 * (attempt + 1))


def _fsync_directory(directory: Path) -> None:
    """Persist a rename on POSIX; Windows has no directory fsync equivalent."""
    if os.name == "nt":
        return
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def acquire_file_lock(path: Path, timeout: float):
    """Lock one byte at offset 0 of ``path``; returns an open fd to release."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR)
    deadline = time.monotonic() + max(timeout, 0.0)
    while True:
        try:
            if os.name == "nt":
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if time.monotonic() >= deadline:
                os.close(fd)
                raise LockBusyError(
                    f"项目文件锁在 {timeout:.0f}s 内未能获得：{path}"
                ) from None
            time.sleep(LOCK_RETRY_INTERVAL)


def release_file_lock(fd) -> None:
    try:
        if os.name == "nt":
            try:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        # Closing the fd releases POSIX flock locks unconditionally.
    finally:
        os.close(fd)
