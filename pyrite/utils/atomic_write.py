"""Crash-safe file replacement that keeps what the file was (#405).

``atomic_write_text`` writes a temp file beside the real file, fsyncs it,
renames it over, and fsyncs the directory, so a crash leaves either the old
content or the new, never a truncated file. A rename makes a new inode, so
it would silently change three things the old ``open(path, "w")`` kept; each
is handled explicitly:

- **Mode and owner.** The temp file gets the original mode, and the
  original uid/gid (always when running as root, otherwise when they
  differ). If the owner cannot be restored, the write falls back to in
  place: a root save must never leave a root-owned file the service user
  cannot read (826e0c14 did).
- **Hard links.** A file with more than one link is written in place: a
  rename would leave the other names holding the old content.
- **A directory the process cannot write** (a read-only mount with one
  writable file, a root-owned ``~/.pyrite``): written in place.

Every fallback logs a warning naming the file and why the write was not
atomic. A symlink is followed: the rename happens in the target's directory,
so the link stays a link.
"""

from __future__ import annotations

import logging
import os
import secrets
import stat
from pathlib import Path

logger = logging.getLogger(__name__)


def _fsync_directory(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:  # a platform that cannot open a directory (Windows)
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_in_place(target: Path, data: bytes, why: str) -> None:
    logger.warning("Writing %s in place, not atomically: %s", target, why)
    with open(target, "r+b") as f:
        f.truncate(0)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def _owner_restored(tmp: str, fd: int, original: os.stat_result) -> bool:
    """Give the temp file the original owner. False when that is not possible."""
    if not hasattr(os, "chown"):
        return True
    mine = os.fstat(fd)
    if os.geteuid() != 0 and (mine.st_uid, mine.st_gid) == (original.st_uid, original.st_gid):
        return True
    try:
        os.chown(tmp, original.st_uid, original.st_gid)
    except OSError:
        return False
    return True


def atomic_write_text(path: str | os.PathLike[str], text: str, *, encoding: str = "utf-8") -> None:
    """Replace ``path`` with ``text`` crash-safely; see the module docstring."""
    data = text.encode(encoding)
    target = Path(os.path.realpath(path))
    try:
        original: os.stat_result | None = os.stat(target)
    except FileNotFoundError:
        original = None

    if original is not None and original.st_nlink > 1:
        _write_in_place(target, data, f"it has {original.st_nlink} hard links")
        return

    tmp = str(target.parent / f".{target.name}.{secrets.token_hex(8)}.tmp")
    # An existing file's mode is set explicitly below; a new file gets what
    # open(path, "w") would have given it (0o666 less the umask).
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600 if original else 0o666)
    except OSError as e:
        if original is None:
            raise
        _write_in_place(
            target, data, f"cannot create a file in {target.parent} ({e.strerror or e})"
        )
        return

    fallback: str | None = None
    try:
        try:
            if original is not None:
                if hasattr(os, "fchmod"):
                    os.fchmod(fd, stat.S_IMODE(original.st_mode))
                if not _owner_restored(tmp, fd, original):
                    fallback = (
                        f"cannot give a new file its owner {original.st_uid}:{original.st_gid}"
                    )
            if fallback is None:
                view = memoryview(data)
                while view:
                    view = view[os.write(fd, view) :]
                os.fsync(fd)
        finally:
            os.close(fd)
        if fallback is None:
            os.replace(tmp, target)
    except BaseException:
        _remove(tmp)
        raise
    if fallback is not None:
        _remove(tmp)
        _write_in_place(target, data, fallback)
        return
    _fsync_directory(target.parent)


def _remove(tmp: str) -> None:
    try:
        os.unlink(tmp)
    except FileNotFoundError:
        pass
