"""Regression tests: IndexManager and MCP loops must enumerate via all_kbs().

Sibling of test_cli_context_db_kbs.py. KBs registered via `pyrite kb add`
live in the DB `kb` table and reach the config only through
``register_db_kbs()`` (the ``_db_kb_cache`` fallback), not
``knowledge_bases``. Any loop over ``config.knowledge_bases`` therefore
silently skips them — exactly what ``all_kbs()``'s docstring warns about.

Covered loops (all previously iterated ``knowledge_bases`` directly):
- IndexManager.check_staleness  — DB-registered KBs never reported stale
- IndexManager.get_index_stats  — DB-registered KBs absent from stats
- IndexManager.check_health     — unindexed/undeclared-type checks skipped
- PyriteMCPServer._list_edge_types — edge types in DB-registered KBs invisible
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import PyriteConfig, Settings
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager

ENTRY_MD = "---\ntitle: Hello\ntype: note\n---\n\nBody text.\n"

KB_YAML_WITH_EDGE = """\
name: some-kb
types:
  ownership:
    description: Ownership relationship
    edge_type: true
    endpoints:
      source:
        field: owner
        accepts: [person]
      target:
        field: asset
        accepts: [asset]
"""


@pytest.fixture
def db_kb_env():
    """Config whose only KB is DB-registered (source='user'), with one
    entry file on disk. knowledge_bases stays empty — the KB is reachable
    solely through all_kbs()/get_kb()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "some-kb"
        kb_path.mkdir()
        (kb_path / "hello.md").write_text(ENTRY_MD)

        db = PyriteDB(db_path)
        db.register_kb(
            name="some-kb",
            kb_type="generic",
            path=str(kb_path),
            description="DB-registered KB",
            source="user",
        )

        config = PyriteConfig(knowledge_bases=[], settings=Settings(index_path=db_path))
        config.register_db_kbs(
            [{"name": "some-kb", "path": str(kb_path), "kb_type": "generic", "description": ""}]
        )
        yield {"config": config, "db": db, "kb_path": kb_path, "db_path": db_path}
        db.close()


class TestIndexManagerCoversDbRegisteredKBs:
    def test_check_staleness_reports_db_registered_kb(self, db_kb_env):
        """A never-indexed DB-registered KB with a file on disk is stale."""
        mgr = IndexManager(db_kb_env["db"], db_kb_env["config"])
        stale = mgr.check_staleness()
        assert "some-kb" in [s["kb"] for s in stale], (
            "check_staleness() must enumerate DB-registered KBs — "
            "an un-indexed `kb add` KB should be reported stale"
        )

    def test_get_index_stats_includes_db_registered_kb(self, db_kb_env):
        """After indexing, stats must count the DB-registered KB's entries."""
        mgr = IndexManager(db_kb_env["db"], db_kb_env["config"])
        assert mgr.index_kb("some-kb") == 1
        stats = mgr.get_index_stats()
        assert "some-kb" in stats["kbs"], (
            "get_index_stats() must enumerate DB-registered KBs"
        )

    def test_check_health_flags_unindexed_file_in_db_registered_kb(self, db_kb_env):
        """A file on disk but not in the index must show as unindexed."""
        mgr = IndexManager(db_kb_env["db"], db_kb_env["config"])
        health = mgr.check_health()
        assert any(u["kb"] == "some-kb" for u in health["unindexed_files"]), (
            "check_health() must enumerate DB-registered KBs — "
            "their unindexed files should be flagged"
        )

    def test_check_health_flags_undeclared_type_in_db_registered_kb(self, db_kb_env):
        """With a kb.yaml present, an off-schema entry_type must be flagged."""
        kb_path = db_kb_env["kb_path"]
        (kb_path / "kb.yaml").write_text("name: some-kb\ntypes:\n  note:\n    description: A note\n")
        (kb_path / "weird.md").write_text(
            "---\ntitle: Weird\ntype: mystery_type\n---\n\nBody.\n"
        )
        mgr = IndexManager(db_kb_env["db"], db_kb_env["config"])
        mgr.index_kb("some-kb")
        health = mgr.check_health()
        assert any(
            u["kb"] == "some-kb" and u["type"] == "mystery_type"
            for u in health["undeclared_types"]
        ), "check_health() undeclared-type sweep must cover DB-registered KBs"


class TestMCPListEdgeTypesCoversDbRegisteredKBs:
    def test_list_edge_types_sees_db_registered_kb(self):
        """Edge types declared in a `kb add` KB's kb.yaml must be listed."""
        from pyrite.server.mcp_server import PyriteMCPServer

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            db_path = tmpdir / "index.db"
            kb_path = tmpdir / "some-kb"
            kb_path.mkdir()
            (kb_path / "kb.yaml").write_text(KB_YAML_WITH_EDGE)

            db = PyriteDB(db_path)
            db.register_kb(
                name="some-kb",
                kb_type="generic",
                path=str(kb_path),
                description="DB-registered KB",
                source="user",
            )
            db.close()

            config = PyriteConfig(
                knowledge_bases=[], settings=Settings(index_path=db_path)
            )
            server = PyriteMCPServer(config=config, tier="read")
            try:
                result = server._list_edge_types({})
            finally:
                server.db.close()
            names = [et["type"] for et in result.get("edge_types", [])]
            assert "ownership" in names, (
                "list_edge_types must enumerate DB-registered KBs via all_kbs()"
            )
