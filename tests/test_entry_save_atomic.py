"""Entry.save() must be atomic: a reader never sees a half-written file.

Two agents on one KB race constantly (claim vs reset, claim vs claim). With a
plain write_text() a concurrent repo.load() can read a truncated or empty file
and fail to parse it; the loser then bails out of a multi-step operation with
file and index disagreeing. Write to a temp file in the same directory and
os.replace() it: atomic on POSIX and Windows, and a failed write leaves the old
content untouched.
"""

import os

import pytest

from pyrite.models.core_types import NoteEntry


def test_failed_write_leaves_previous_content_intact(tmp_path, monkeypatch):
    path = tmp_path / "note.md"
    NoteEntry(id="note", title="v1", body="first").save(path)
    before = path.read_text()

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        NoteEntry(id="note", title="v2", body="second").save(path)

    assert path.read_text() == before, "a failed save must not corrupt the file"
    assert [p.name for p in tmp_path.iterdir()] == ["note.md"], "no temp file left behind"


def test_save_goes_through_replace(tmp_path, monkeypatch):
    calls = []
    real = os.replace

    def spy(src, dst):
        calls.append((str(src), str(dst)))
        return real(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    path = tmp_path / "note.md"
    NoteEntry(id="note", title="t", body="b").save(path)
    assert calls and calls[-1][1] == str(path)
    assert os.path.dirname(calls[-1][0]) == str(tmp_path), "temp file must be in the same dir"
    assert "first" not in path.read_text() and path.read_text().endswith("b\n")


def test_new_file_mode_follows_umask_not_mkstemp(tmp_path):
    # mkstemp creates 0600; a KB served or shared by other users must get the
    # same mode a plain write would have produced under the current umask.
    old = os.umask(0o022)
    try:
        path = tmp_path / "note.md"
        NoteEntry(id="note", title="t", body="b").save(path)
        assert oct(path.stat().st_mode & 0o777) == oct(0o644)
    finally:
        os.umask(old)


def test_existing_file_mode_is_preserved(tmp_path):
    path = tmp_path / "note.md"
    NoteEntry(id="note", title="t", body="b").save(path)
    os.chmod(path, 0o600)
    NoteEntry(id="note", title="t2", body="b2").save(path)
    assert oct(path.stat().st_mode & 0o777) == oct(0o600)


class TestExclusiveSave:
    """#391 cold read round 2 item 2: `exclusive=True` closes the TOCTOU
    window between the write pipeline's own exists() check and the write
    that follows it -- `os.replace` always succeeds even if the target
    exists, so two truly concurrent creates could both pass the check and
    the second would silently overwrite the first. `os.link` fails with
    `FileExistsError` if the target already exists, atomically.
    """

    def test_exclusive_save_succeeds_when_target_does_not_exist(self, tmp_path):
        path = tmp_path / "note.md"
        NoteEntry(id="note", title="t", body="b").save(path, exclusive=True)
        assert path.exists()
        assert "b" in path.read_text()

    def test_exclusive_save_refuses_an_existing_target(self, tmp_path):
        path = tmp_path / "note.md"
        NoteEntry(id="note", title="t", body="ORIGINAL").save(path)
        original = path.read_text()

        with pytest.raises(FileExistsError):
            NoteEntry(id="note", title="t", body="REPLACED").save(path, exclusive=True)

        assert path.read_text() == original, "an exclusive save must never overwrite"

    def test_exclusive_save_leaves_no_temp_file_on_refusal(self, tmp_path):
        path = tmp_path / "note.md"
        NoteEntry(id="note", title="t", body="ORIGINAL").save(path)

        with pytest.raises(FileExistsError):
            NoteEntry(id="note", title="t", body="REPLACED").save(path, exclusive=True)

        assert [p.name for p in tmp_path.iterdir()] == ["note.md"], "no temp file left behind"

    @pytest.mark.control(
        reason="exclusive=False is the default and was the only behavior "
        "before this change, so save() overwriting is exactly what dev "
        "already did -- this is a regression guard for the untouched path, "
        "not a test of the new exclusive=True behavior"
    )
    def test_non_exclusive_save_still_overwrites(self, tmp_path):
        """Regression guard: exclusive=False (the default, every update)
        must keep working exactly as before -- this is what makes create
        different from update, not a global behavior change."""
        path = tmp_path / "note.md"
        NoteEntry(id="note", title="t", body="ORIGINAL").save(path)
        NoteEntry(id="note", title="t", body="REPLACED").save(path)
        assert "REPLACED" in path.read_text()
