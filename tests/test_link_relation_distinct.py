"""A link's duplicate key is (target, kb, relation), not (target, kb) (#396).

`pyrite link a b -r implements` then `pyrite link a b -r supersedes` used to
report `Linked:` for the second call too but write nothing -- the duplicate
check in `KBService.add_link` ignored `relation`, so a second, different
relation between the same two entries could never be recorded. `backlinks`
then showed only the first relation.

This file also pins the reporting and rendering bugs the groom named:
- a genuine no-op (identical target+kb+relation) is reported as one
  (`Already linked:` / `created: False`), not as `Linked:` / `created: True`;
- re-issuing that no-op after the target is deleted stays a no-op (the
  existing idempotency the duplicate check was written for);
- the relation name survives in the CLI confirmation, including on the
  `--bidi` inverse line -- Rich was parsing `--[implements]-->` as a style
  tag and swallowing it.
"""

import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import NoteEntry
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


@pytest.fixture
def link_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        notes_path = tmpdir / "notes"
        notes_path.mkdir()
        notes_kb = KBConfig(name="lk", path=notes_path, kb_type=KBType.GENERIC)
        config = PyriteConfig(knowledge_bases=[notes_kb], settings=Settings(index_path=db_path))
        repo = KBRepository(notes_kb)
        for eid in ("link-a", "link-b"):
            repo.save(NoteEntry(id=eid, title=eid, body=f"Body for {eid}."))
        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()
        db.close()
        yield {"config": config, "tmpdir": tmpdir, "notes_path": notes_path, "db_path": db_path}


def _patch_config(env):
    import contextlib

    @contextlib.contextmanager
    def _multi_patch():
        with patch("pyrite.cli.load_config", return_value=env["config"]):
            with patch("pyrite.cli.context.load_config", return_value=env["config"]):
                yield

    return _multi_patch()


# ---------------------------------------------------------------------------
# Service-level: KBService.add_link
# ---------------------------------------------------------------------------


def test_add_link_with_a_different_relation_is_created_not_skipped(link_env):
    db = PyriteDB(link_env["db_path"])
    try:
        svc = KBService(link_env["config"], db)
        r1 = svc.add_link("link-a", "lk", "link-b", relation="implements")
        assert r1["created"] is True

        r2 = svc.add_link("link-a", "lk", "link-b", relation="supersedes")
        assert r2["created"] is True

        repo = KBRepository(link_env["config"].get_kb("lk"))
        entry = repo.load("link-a")
        relations = {lnk.relation for lnk in entry.links}
        assert relations == {"implements", "supersedes"}, relations
    finally:
        db.close()


def test_add_link_identical_triple_is_a_noop_and_reports_created_false(link_env):
    db = PyriteDB(link_env["db_path"])
    try:
        svc = KBService(link_env["config"], db)
        svc.add_link("link-a", "lk", "link-b", relation="implements")

        path = list(link_env["notes_path"].rglob("link-a.md"))[0]
        before = path.read_text(encoding="utf-8")

        result = svc.add_link("link-a", "lk", "link-b", relation="implements")
        assert result["created"] is False

        after = path.read_text(encoding="utf-8")
        assert after == before
    finally:
        db.close()


def test_add_link_identical_triple_stays_a_noop_after_target_deleted(link_env):
    """The idempotency the duplicate check exists for: a replayed link set
    must not fail just because the target has since gone."""
    db = PyriteDB(link_env["db_path"])
    try:
        svc = KBService(link_env["config"], db)
        svc.add_link("link-a", "lk", "link-b", relation="implements")

        # Through the service's own delete, so the index row goes with the
        # file -- an `unlink()` on disk alone would leave the index stale and
        # `resolved` would read the deleted target as still there.
        assert svc.delete_entry("link-b", "lk") is True

        result = svc.add_link("link-a", "lk", "link-b", relation="implements")
        assert result["created"] is False
        assert result["resolved"] is False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI: pyrite link
# ---------------------------------------------------------------------------


def test_cli_link_second_relation_is_appended(link_env):
    with _patch_config(link_env):
        r1 = runner.invoke(app, ["link", "link-a", "link-b", "-k", "lk", "-r", "implements"])
        assert r1.exit_code == 0, r1.output
        r2 = runner.invoke(app, ["link", "link-a", "link-b", "-k", "lk", "-r", "supersedes"])
        assert r2.exit_code == 0, r2.output

    repo = KBRepository(link_env["config"].get_kb("lk"))
    entry = repo.load("link-a")
    relations = {lnk.relation for lnk in entry.links}
    assert relations == {"implements", "supersedes"}, relations


def test_cli_link_duplicate_prints_already_linked(link_env):
    with _patch_config(link_env):
        r1 = runner.invoke(app, ["link", "link-a", "link-b", "-k", "lk", "-r", "implements"])
        assert r1.exit_code == 0, r1.output
        assert "Linked:" in _strip_ansi(r1.output)

        r2 = runner.invoke(app, ["link", "link-a", "link-b", "-k", "lk", "-r", "implements"])
        assert r2.exit_code == 0, r2.output
        clean = _strip_ansi(r2.output)
        assert "Already linked:" in clean
        assert "Linked:" not in clean.replace("Already linked:", "")


def test_cli_link_confirmation_shows_the_relation(link_env):
    with _patch_config(link_env):
        result = runner.invoke(app, ["link", "link-a", "link-b", "-k", "lk", "-r", "implements"])
        assert result.exit_code == 0, result.output
    clean = _strip_ansi(result.output)
    assert "implements" in clean, clean


def test_cli_link_bidi_confirmation_shows_the_inverse_relation(link_env):
    with _patch_config(link_env):
        result = runner.invoke(
            app, ["link", "link-a", "link-b", "-k", "lk", "-r", "implements", "--bidi"]
        )
        assert result.exit_code == 0, result.output
    clean = _strip_ansi(result.output)
    # Two confirmation lines: forward relation and its inverse.
    assert "implements" in clean, clean
    from pyrite.schema import get_inverse_relation

    assert get_inverse_relation("implements") in clean, clean
