"""Tests for link CLI commands (pyrite links broken/wanted).

Uses shared fixtures and config patching from test_cli_commands.
"""

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import EventEntry
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository

runner = CliRunner()


@pytest.fixture
def link_env():
    """Environment for link command tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        events_path = tmpdir / "events"
        events_path.mkdir()

        events_kb = KBConfig(
            name="test-events",
            path=events_path,
            kb_type=KBType.EVENTS,
        )

        config = PyriteConfig(
            knowledge_bases=[events_kb],
            settings=Settings(index_path=db_path),
        )

        # Create sample event
        repo = KBRepository(events_kb)
        event = EventEntry.create(
            date="2025-01-10",
            title="Test Event 0",
            body="Body for event 0.",
            importance=5,
        )
        repo.save(event)

        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()
        db.close()

        yield {"config": config, "tmpdir": tmpdir}


def _patch_config(env):
    """Patch load_config to return test config."""
    import contextlib
    from unittest.mock import patch

    @contextlib.contextmanager
    def _multi_patch():
        with patch("pyrite.cli.load_config", return_value=env["config"]):
            with patch("pyrite.cli.context.load_config", return_value=env["config"]):
                yield

    return _multi_patch()


@pytest.mark.cli
class TestLinksBroken:
    def test_links_broken_empty(self, link_env):
        """Clean KB shows no broken links."""
        with _patch_config(link_env):
            result = runner.invoke(app, ["links", "broken"])
            assert result.exit_code == 0
            assert "No broken links" in result.output

    def test_links_broken_with_results(self, link_env):
        """Broken links are shown when present."""
        from pyrite.services.kb_service import KBService

        config = link_env["config"]
        db = PyriteDB(config.settings.index_path)
        svc = KBService(config, db)
        svc.create_entry(
            "test-events",
            "broken-link-entry",
            "Entry with broken link",
            "note",
            body="See [[no-such-page]].",
        )
        IndexManager(db, config).sync_incremental("test-events")
        db.close()

        with _patch_config(link_env):
            result = runner.invoke(app, ["links", "broken", "--format", "json"])
            assert result.exit_code == 0
            import json

            data = json.loads(result.output)
            assert data["count"] >= 1
            targets = [l["target_id"] for l in data["broken_links"]]
            assert "no-such-page" in targets

    def test_links_broken_json(self, link_env):
        """JSON format includes count and broken_links array."""
        with _patch_config(link_env):
            result = runner.invoke(app, ["links", "broken", "--format", "json"])
            assert result.exit_code == 0
            import json

            data = json.loads(result.output)
            assert "count" in data
            assert "broken_links" in data


@pytest.mark.cli
class TestLinksWanted:
    def test_links_wanted_empty(self, link_env):
        """Clean KB shows no wanted pages."""
        with _patch_config(link_env):
            result = runner.invoke(app, ["links", "wanted"])
            assert result.exit_code == 0
            assert "No wanted pages" in result.output

    def test_links_wanted_json(self, link_env):
        """JSON format includes count and wanted_pages array."""
        with _patch_config(link_env):
            result = runner.invoke(app, ["links", "wanted", "--format", "json"])
            assert result.exit_code == 0
            import json

            data = json.loads(result.output)
            assert "count" in data
            assert "wanted_pages" in data


@pytest.mark.cli
class TestIndexHealthBrokenLinks:
    def test_index_health_includes_broken_links(self, link_env):
        """Health check JSON output includes broken_links count."""
        with _patch_config(link_env):
            result = runner.invoke(app, ["index", "health", "--format", "json"])
            assert result.exit_code == 0
            import json

            data = json.loads(result.output)
            assert "broken_links" in data

    def test_index_health_broken_links_warning(self, link_env):
        """Health check shows warning status when broken links exist."""
        from pyrite.services.kb_service import KBService

        config = link_env["config"]
        db = PyriteDB(config.settings.index_path)
        svc = KBService(config, db)
        svc.create_entry(
            "test-events",
            "health-broken",
            "Health broken link",
            "note",
            body="See [[health-missing-target]].",
        )
        IndexManager(db, config).sync_incremental("test-events")
        db.close()

        with _patch_config(link_env):
            result = runner.invoke(app, ["index", "health", "--format", "json"])
            assert result.exit_code == 0
            import json

            data = json.loads(result.output)
            assert data["status"] == "warning"
            assert data["broken_links"] >= 1
