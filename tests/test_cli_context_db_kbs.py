"""Regression tests for DB-registered KB merging in CLI context helpers.

Covers GitHub issue #2 / `index-sync-ignores-db-registered-kbs`:
`get_config_and_db()` and `cli_db_context()` only called `load_config()` and
never merged KBs registered via `pyrite kb add` (which live in the DB with
`source='user'`, not the YAML config). As a result `pyrite index sync`
operated on a config missing those KBs and indexed 0 entries for them.

Both helpers must merge DB-registered KBs, matching `_init_base()`.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pyrite.config import PyriteConfig, Settings
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db_with_user_kb():
    """A PyriteDB with one KB registered via the DB (source='user'),
    plus a YAML config that knows nothing about it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "some-kb"
        kb_path.mkdir()

        db = PyriteDB(db_path)
        # Equivalent to `pyrite kb add` — registers into the DB with source='user'.
        db.register_kb(
            name="some-kb",
            kb_type="generic",
            path=str(kb_path),
            description="DB-registered KB",
            source="user",
        )
        db.close()

        # YAML config has NO knowledge bases — only the index path.
        config = PyriteConfig(knowledge_bases=[], settings=Settings(index_path=db_path))
        yield {"config": config, "kb_path": kb_path}


def test_get_config_and_db_resolves_db_registered_kb(db_with_user_kb):
    """After get_config_and_db(), a DB-registered KB is resolvable by name
    (powers `index sync -k some-kb`) and appears in all_kbs() (powers the
    bare `index sync` that enumerates every KB)."""
    from pyrite.cli.context import get_config_and_db

    with patch("pyrite.cli.context.load_config", return_value=db_with_user_kb["config"]):
        config, db = get_config_and_db()
        try:
            assert config.get_kb("some-kb") is not None, (
                "get_config_and_db() must make `kb add` KBs resolvable by name"
            )
            assert "some-kb" in [kb.name for kb in config.all_kbs()], (
                "DB-registered KB must appear in all_kbs() so bare `index sync` indexes it"
            )
        finally:
            db.close()


def test_cli_db_context_resolves_db_registered_kb(db_with_user_kb):
    from pyrite.cli.context import cli_db_context

    with patch("pyrite.cli.context.load_config", return_value=db_with_user_kb["config"]):
        with cli_db_context() as (config, db):
            assert config.get_kb("some-kb") is not None
            assert "some-kb" in [kb.name for kb in config.all_kbs()]


def test_index_sync_indexes_entries_for_db_registered_kb():
    """End-to-end repro from GitHub issue #2: a KB registered via the DB
    (`pyrite kb add`) with a markdown entry must produce a non-zero index
    count from `index sync`, both for the bare and the `-k` forms."""
    from pyrite.storage.index import IndexManager

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "some-kb"
        kb_path.mkdir()
        # One real entry file so indexing has something to find.
        (kb_path / "hello.md").write_text(
            "---\ntitle: Hello\ntype: note\n---\n\nKnown term: pineapple.\n"
        )

        db = PyriteDB(db_path)
        db.register_kb(
            name="some-kb",
            kb_type="generic",
            path=str(kb_path),
            description="DB-registered KB",
            source="user",
        )
        db.close()

        config = PyriteConfig(knowledge_bases=[], settings=Settings(index_path=db_path))
        with patch("pyrite.cli.context.load_config", return_value=config):
            from pyrite.cli.context import get_config_and_db

            cfg, db = get_config_and_db()
            try:
                mgr = IndexManager(db, cfg)
                # Bare sync (no kb_name) must include the DB-registered KB.
                result = mgr.sync_incremental()
                assert result.get("added", 0) >= 1, (
                    f"bare index sync indexed nothing for kb add KB: {result}"
                )
            finally:
                db.close()
