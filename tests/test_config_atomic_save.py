"""config.yaml saves are crash-safe and keep what the file was (#405).

``save_config`` used to write with ``open(path, "w")``, which truncates first:
a crash mid-write left an empty or half-written registry. The first fix
(826e0c14, reverted) wrote a temp file and renamed it over, and in doing so
gave a root save a root-owned file the service user could not read, broke
hard links, failed in a read-only directory and never fsynced.

Every property of the save is pinned here, each by the surface it runs on:
``save_config`` in-process against a real temp directory, with ``os``
functions spied or failed where the property is a syscall (fsync, chown, a
crash between write and rename).
"""

import grp
import logging
import os
import stat

import pytest

import pyrite.config as config_module
from pyrite.config import KBConfig, PyriteConfig, load_config, save_config
from pyrite.utils.yaml import dump_yaml_file, load_yaml_file


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    d = tmp_path / "cfg"
    d.mkdir()
    monkeypatch.setattr(config_module, "CONFIG_DIR", d)
    monkeypatch.setattr(config_module, "CONFIG_FILE", d / "config.yaml")
    monkeypatch.delenv("PYRITE_DATA_DIR", raising=False)
    return d


def _kb(tmp_path, name) -> KBConfig:
    path = tmp_path / "kbs" / name
    path.mkdir(parents=True, exist_ok=True)
    return KBConfig(name=name, path=path, kb_type="generic")


def _write_registry(directory, tmp_path, *names) -> bytes:
    config = PyriteConfig(knowledge_bases=[_kb(tmp_path, n) for n in names])
    dump_yaml_file(config.to_dict(), directory / "config.yaml")
    return (directory / "config.yaml").read_bytes()


def _names(path) -> list[str]:
    return [kb["name"] for kb in load_yaml_file(path).get("knowledge_bases") or []]


def _config_with_b(tmp_path) -> PyriteConfig:
    config = load_config()
    config.add_kb(_kb(tmp_path, "b"))
    return config


def _leftovers(directory) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name != "config.yaml")


# ---------------------------------------------------------------------------
# Crash safety: temp file, fsync, rename, directory fsync
# ---------------------------------------------------------------------------


def test_a_crash_between_write_and_rename_leaves_the_old_file(cfg_dir, tmp_path, monkeypatch):
    before = _write_registry(cfg_dir, tmp_path, "a")
    config = _config_with_b(tmp_path)

    def crash(*args, **kwargs):
        raise OSError("simulated crash before the rename")

    monkeypatch.setattr(os, "replace", crash)
    with pytest.raises(OSError, match="simulated crash"):
        save_config(config)

    assert (cfg_dir / "config.yaml").read_bytes() == before
    assert _leftovers(cfg_dir) == [], "the temp file is removed when the save fails"


def test_a_failed_fsync_leaves_the_old_file(cfg_dir, tmp_path, monkeypatch):
    """The data is on disk before the rename can publish it."""
    before = _write_registry(cfg_dir, tmp_path, "a")
    config = _config_with_b(tmp_path)

    def fail(fd):
        raise OSError("simulated I/O error on fsync")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="fsync"):
        save_config(config)

    assert (cfg_dir / "config.yaml").read_bytes() == before
    assert _leftovers(cfg_dir) == []


def test_the_temp_file_and_the_directory_are_fsynced_around_the_rename(
    cfg_dir, tmp_path, monkeypatch
):
    _write_registry(cfg_dir, tmp_path, "a")
    config = _config_with_b(tmp_path)
    events = []
    real_fsync, real_replace = os.fsync, os.replace

    def spy_fsync(fd):
        st = os.fstat(fd)
        events.append(("fsync", "dir" if stat.S_ISDIR(st.st_mode) else "file", st.st_ino))
        return real_fsync(fd)

    def spy_replace(src, dst, *a, **kw):
        events.append(("replace", str(dst)))
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "fsync", spy_fsync)
    monkeypatch.setattr(os, "replace", spy_replace)
    save_config(config)

    new_ino = (cfg_dir / "config.yaml").stat().st_ino
    dir_ino = cfg_dir.stat().st_ino
    assert events == [
        ("fsync", "file", new_ino),
        ("replace", str((cfg_dir / "config.yaml").resolve())),
        ("fsync", "dir", dir_ino),
    ]
    assert _names(cfg_dir / "config.yaml") == ["a", "b"]
    assert _leftovers(cfg_dir) == []


def test_a_first_save_with_no_file_is_atomic_too(cfg_dir, tmp_path, monkeypatch):
    replaced = []
    real_replace = os.replace
    monkeypatch.setattr(
        os, "replace", lambda s, d, *a, **k: replaced.append(d) or real_replace(s, d, *a, **k)
    )
    save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "x")]))
    assert replaced == [(cfg_dir / "config.yaml").resolve()]
    assert _names(cfg_dir / "config.yaml") == ["x"]
    assert _leftovers(cfg_dir) == []


# ---------------------------------------------------------------------------
# Mode and owner
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", [0o640, 0o600, 0o644])
def test_the_file_mode_is_kept(cfg_dir, tmp_path, mode):
    _write_registry(cfg_dir, tmp_path, "a")
    (cfg_dir / "config.yaml").chmod(mode)
    ino = (cfg_dir / "config.yaml").stat().st_ino

    save_config(_config_with_b(tmp_path))

    st = (cfg_dir / "config.yaml").stat()
    assert st.st_ino != ino, "the save renamed a new file into place"
    assert stat.S_IMODE(st.st_mode) == mode


def test_a_root_save_gives_the_new_file_the_original_owner(cfg_dir, tmp_path, monkeypatch):
    """`docker exec -u root ... pyrite-admin` must not leave a root-owned
    config.yaml the service user cannot read."""
    _write_registry(cfg_dir, tmp_path, "a")
    st = (cfg_dir / "config.yaml").stat()
    events = []
    real_chown, real_replace = os.chown, os.replace

    def spy_chown(path, uid, gid, *a, **kw):
        events.append(("chown", uid, gid))
        return real_chown(path, uid, gid, *a, **kw)

    def spy_replace(src, dst, *a, **kw):
        events.append(("replace",))
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(os, "chown", spy_chown)
    monkeypatch.setattr(os, "replace", spy_replace)
    save_config(_config_with_b(tmp_path))

    assert events == [("chown", st.st_uid, st.st_gid), ("replace",)]
    assert _names(cfg_dir / "config.yaml") == ["a", "b"]


def test_an_owner_that_cannot_be_kept_means_an_in_place_write(
    cfg_dir, tmp_path, monkeypatch, caplog
):
    """When chown fails the rename would hand the file to this process's
    user; writing in place keeps the owner, and says so."""
    _write_registry(cfg_dir, tmp_path, "a")
    ino = (cfg_dir / "config.yaml").stat().st_ino

    def refuse(*args, **kwargs):
        raise PermissionError("simulated: cannot chown")

    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(os, "chown", refuse)
    with caplog.at_level(logging.WARNING):
        save_config(_config_with_b(tmp_path))

    assert (cfg_dir / "config.yaml").stat().st_ino == ino
    assert _names(cfg_dir / "config.yaml") == ["a", "b"]
    assert _leftovers(cfg_dir) == []
    assert any("in place" in r.getMessage() for r in caplog.records)


def _another_group_of_mine() -> int | None:
    mine = os.getgroups()
    for gid in mine:
        if gid != os.getegid():
            return gid
    return None


@pytest.mark.skipif(os.geteuid() == 0, reason="a non-root owner check")
def test_a_non_root_save_keeps_a_group_it_belongs_to(cfg_dir, tmp_path):
    """A new file takes the process's group (Linux) or the directory's (BSD);
    the save puts the original group back."""
    other = _another_group_of_mine()
    if other is None:
        pytest.skip("this user belongs to only one group")
    _write_registry(cfg_dir, tmp_path, "a")
    os.chown(cfg_dir / "config.yaml", -1, other)
    ino = (cfg_dir / "config.yaml").stat().st_ino

    save_config(_config_with_b(tmp_path))

    st = (cfg_dir / "config.yaml").stat()
    assert st.st_gid == other, grp.getgrgid(st.st_gid).gr_name
    assert st.st_ino != ino


# ---------------------------------------------------------------------------
# Fallbacks: a directory the process cannot write, a hard-linked file
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write a 0o555 directory")
def test_a_read_only_directory_means_an_in_place_write_and_a_warning(cfg_dir, tmp_path, caplog):
    _write_registry(cfg_dir, tmp_path, "a")
    config = _config_with_b(tmp_path)
    ino = (cfg_dir / "config.yaml").stat().st_ino
    cfg_dir.chmod(0o555)
    try:
        with caplog.at_level(logging.WARNING):
            save_config(config)
    finally:
        cfg_dir.chmod(0o755)

    assert (cfg_dir / "config.yaml").stat().st_ino == ino
    assert _names(cfg_dir / "config.yaml") == ["a", "b"]
    assert any(
        "in place" in r.getMessage() and str(cfg_dir) in r.getMessage() for r in caplog.records
    )


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write a 0o555 directory")
def test_a_read_only_directory_with_no_file_still_fails(cfg_dir, tmp_path):
    """There is nothing to write in place: the error is the directory's."""
    cfg_dir.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
            save_config(PyriteConfig(knowledge_bases=[_kb(tmp_path, "x")]))
    finally:
        cfg_dir.chmod(0o755)
    assert not (cfg_dir / "config.yaml").exists()


def test_a_hard_linked_file_is_written_in_place_with_a_warning(
    cfg_dir, tmp_path, monkeypatch, caplog
):
    """A rename cannot keep a hard link; the link is what the title promises."""
    _write_registry(cfg_dir, tmp_path, "a")
    alias = tmp_path / "alias.yaml"
    os.link(cfg_dir / "config.yaml", alias)
    replaced = []
    monkeypatch.setattr(os, "replace", lambda *a, **k: replaced.append(a))

    with caplog.at_level(logging.WARNING):
        save_config(_config_with_b(tmp_path))

    assert replaced == []
    assert os.path.samefile(cfg_dir / "config.yaml", alias)
    assert _names(alias) == ["a", "b"]
    assert any("hard link" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Symlinks
# ---------------------------------------------------------------------------


def test_a_symlinked_config_stays_a_symlink_and_its_target_is_replaced_atomically(
    cfg_dir, tmp_path, monkeypatch
):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    _write_registry(real_dir, tmp_path, "a")
    real = real_dir / "config.yaml"
    (cfg_dir / "config.yaml").symlink_to(real)
    ino = real.stat().st_ino
    replaced = []
    real_replace = os.replace

    def spy_replace(src, dst, *a, **kw):
        replaced.append((os.path.dirname(os.path.abspath(src)), str(dst)))
        return real_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", spy_replace)
    save_config(_config_with_b(tmp_path))

    assert (cfg_dir / "config.yaml").is_symlink()
    assert os.readlink(cfg_dir / "config.yaml") == str(real)
    assert replaced == [(str(real_dir.resolve()), str(real.resolve()))]
    assert real.stat().st_ino != ino
    assert _names(real) == ["a", "b"]
    assert _leftovers(cfg_dir) == [] and _leftovers(real_dir) == []
