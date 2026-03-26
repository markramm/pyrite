"""Tests for pyrite links orphans command (cross-KB orphan detection)."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.cli.link_commands import _find_orphans
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

runner = CliRunner()


@pytest.fixture
def orphan_env():
    """Two KBs where some entries have cross-KB links and others don't."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        kb_a_path = tmpdir / "kb-a"
        kb_a_path.mkdir()
        kb_b_path = tmpdir / "kb-b"
        kb_b_path.mkdir()

        kb_a = KBConfig(name="kb-a", path=kb_a_path, kb_type=KBType.GENERIC)
        kb_b = KBConfig(name="kb-b", path=kb_b_path, kb_type=KBType.GENERIC)

        config = PyriteConfig(
            knowledge_bases=[kb_a, kb_b],
            settings=Settings(index_path=db_path),
        )

        db = PyriteDB(db_path)
        svc = KBService(config, db)

        # High-importance entry WITH cross-KB link (not orphan)
        svc.create_entry("kb-a", "linked-concept", "Linked Concept",
                         body="This concept about trust is well-connected.",
                         entry_type="concept", tags=["trust"])
        svc.update_entry("linked-concept", "kb-a", importance=9)
        svc.create_entry("kb-b", "linked-target", "Linked Target",
                         body="Trust and coordination in organizations.",
                         entry_type="concept", tags=["trust"])
        svc.add_link("linked-concept", "kb-a", "linked-target",
                     target_kb="kb-b", relation="related_to")

        # High-importance entry WITHOUT cross-KB link (orphan candidate)
        svc.create_entry("kb-a", "orphan-concept", "Orphan Concept",
                         body="Feedback loops and systems thinking patterns.",
                         entry_type="concept", tags=["systems", "feedback"])
        svc.update_entry("orphan-concept", "kb-a", importance=8)
        # Create a matching entry in kb-b that COULD be linked
        svc.create_entry("kb-b", "systems-match", "System Dynamics",
                         body="System dynamics models feedback loops and delays.",
                         entry_type="concept", tags=["systems", "feedback"])

        # Low-importance entry (should be filtered out)
        svc.create_entry("kb-a", "low-importance", "Low Importance Note",
                         body="Just a casual note about cooking.",
                         entry_type="note", tags=["cooking"])

        yield {"config": config, "db": db, "svc": svc}
        db.close()


class TestFindOrphans:
    def test_finds_orphan_entries(self, orphan_env):
        results = _find_orphans(
            kb_name="kb-a",
            min_importance=7,
            limit=10,
            config=orphan_env["config"],
            db=orphan_env["db"],
        )
        ids = [r["id"] for r in results]
        # orphan-concept should appear (high importance, no cross-KB links, has potential matches)
        assert "orphan-concept" in ids

    def test_linked_entries_ranked_lower(self, orphan_env):
        results = _find_orphans(
            kb_name="kb-a",
            min_importance=7,
            limit=10,
            config=orphan_env["config"],
            db=orphan_env["db"],
        )
        ids = [r["id"] for r in results]
        if "linked-concept" in ids and "orphan-concept" in ids:
            # orphan should be ranked higher (more orphan-ness)
            assert ids.index("orphan-concept") < ids.index("linked-concept")

    def test_filters_by_importance(self, orphan_env):
        results = _find_orphans(
            kb_name="kb-a",
            min_importance=7,
            limit=10,
            config=orphan_env["config"],
            db=orphan_env["db"],
        )
        ids = [r["id"] for r in results]
        assert "low-importance" not in ids

    def test_results_have_required_fields(self, orphan_env):
        results = _find_orphans(
            kb_name="kb-a",
            min_importance=5,
            limit=10,
            config=orphan_env["config"],
            db=orphan_env["db"],
        )
        if results:
            r = results[0]
            assert "id" in r
            assert "title" in r
            assert "importance" in r
            assert "cross_kb_links" in r
            assert "potential_matches" in r
            assert "orphan_score" in r

    def test_respects_limit(self, orphan_env):
        results = _find_orphans(
            kb_name="kb-a",
            min_importance=1,
            limit=1,
            config=orphan_env["config"],
            db=orphan_env["db"],
        )
        assert len(results) <= 1


class TestOrphansCLI:
    def test_cli_json_output(self, orphan_env, monkeypatch):
        monkeypatch.setattr(
            "pyrite.cli.link_commands.get_config_and_db",
            lambda: (orphan_env["config"], orphan_env["db"]),
        )
        orphan_env["db"].close = lambda: None

        result = runner.invoke(
            app, ["links", "orphans", "--kb", "kb-a", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "orphans" in data
        assert data["kb_name"] == "kb-a"
