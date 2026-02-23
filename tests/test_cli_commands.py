"""Tests for Typer CLI commands (pyrite CLI).

Tests create/update/delete/list/timeline/tags/backlinks via the Typer app.
Uses shared fixtures from conftest.py.
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
def cli_env():
    """Environment for Typer CLI tests using monkeypatch-style config override."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        events_path = tmpdir / "events"
        events_path.mkdir()

        research_path = tmpdir / "research"
        research_path.mkdir()
        (research_path / "actors").mkdir()

        events_kb = KBConfig(
            name="test-events",
            path=events_path,
            kb_type=KBType.EVENTS,
        )
        research_kb = KBConfig(
            name="test-research",
            path=research_path,
            kb_type=KBType.RESEARCH,
        )

        config = PyriteConfig(
            knowledge_bases=[events_kb, research_kb],
            settings=Settings(index_path=db_path),
        )

        # Create sample data
        events_repo = KBRepository(events_kb)
        for i in range(3):
            event = EventEntry.create(
                date=f"2025-01-{10 + i:02d}",
                title=f"Test Event {i}",
                body=f"Body for event {i} about immigration.",
                importance=5 + i,
            )
            event.tags = ["test", "immigration"]
            events_repo.save(event)

        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()
        db.close()

        yield {"config": config, "tmpdir": tmpdir, "events_kb": events_kb}


def _patch_config(cli_env):
    """Patch load_config to return test config."""
    from unittest.mock import patch

    return patch("pyrite.cli.load_config", return_value=cli_env["config"])


@pytest.mark.cli
class TestTyperListCommand:
    def test_list_shows_kbs(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "test-events" in result.output

    def test_list_shows_research_kb(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["list"])
            assert "test-research" in result.output


@pytest.mark.cli
class TestTyperGetCommand:
    def test_get_entry_found(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["get", "2025-01-10--test-event-0", "--kb", "test-events"])
            assert result.exit_code == 0
            assert "Test Event 0" in result.output

    def test_get_entry_not_found(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["get", "nonexistent"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower()


@pytest.mark.cli
class TestTyperTimelineCommand:
    def test_timeline_shows_events(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["timeline"])
            assert result.exit_code == 0
            assert "Timeline" in result.output

    def test_timeline_with_date_filter(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["timeline", "--from", "2025-01-11"])
            assert result.exit_code == 0


@pytest.mark.cli
class TestTyperTagsCommand:
    def test_tags_shows_results(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["tags"])
            assert result.exit_code == 0
            assert "Tags" in result.output

    def test_tags_with_kb_filter(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["tags", "--kb", "test-events"])
            assert result.exit_code == 0


@pytest.mark.cli
class TestTyperBacklinksCommand:
    def test_backlinks_no_results(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app, ["backlinks", "2025-01-10--test-event-0", "--kb", "test-events"]
            )
            assert result.exit_code == 0
            assert "No backlinks" in result.output


@pytest.mark.cli
class TestTyperCreateCommand:
    def test_create_note(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "create",
                    "--kb",
                    "test-events",
                    "--type",
                    "note",
                    "--title",
                    "My New Note",
                    "--body",
                    "Some body text",
                ],
            )
            assert result.exit_code == 0
            assert "Created" in result.output

    def test_create_with_tags(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "create",
                    "--kb",
                    "test-events",
                    "--type",
                    "note",
                    "--title",
                    "Tagged Entry",
                    "--tags",
                    "tag1,tag2",
                ],
            )
            assert result.exit_code == 0

    def test_create_nonexistent_kb(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "create",
                    "--kb",
                    "nonexistent",
                    "--type",
                    "note",
                    "--title",
                    "Test",
                ],
            )
            assert result.exit_code == 1
            assert "not found" in result.output.lower() or "Error" in result.output


@pytest.mark.cli
class TestTyperUpdateCommand:
    def test_update_title(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "update",
                    "2025-01-10--test-event-0",
                    "--kb",
                    "test-events",
                    "--title",
                    "Updated Title",
                ],
            )
            assert result.exit_code == 0
            assert "Updated" in result.output

    def test_update_nonexistent(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "update",
                    "nonexistent",
                    "--kb",
                    "test-events",
                    "--title",
                    "New",
                ],
            )
            assert result.exit_code == 1


@pytest.mark.cli
class TestTyperDeleteCommand:
    def test_delete_entry(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                ["delete", "2025-01-10--test-event-0", "--kb", "test-events", "--force"],
            )
            assert result.exit_code == 0
            assert "Deleted" in result.output

    def test_delete_nonexistent(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                ["delete", "nonexistent", "--kb", "test-events", "--force"],
            )
            assert result.exit_code == 1


@pytest.mark.cli
class TestTyperConfigCommand:
    def test_config_shows_info(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0
            assert "Config file" in result.output
