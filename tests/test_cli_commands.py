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
    """Patch load_config to return test config in all CLI modules."""
    import contextlib
    from unittest.mock import patch

    @contextlib.contextmanager
    def _multi_patch():
        with patch("pyrite.cli.load_config", return_value=cli_env["config"]):
            with patch("pyrite.cli.context.load_config", return_value=cli_env["config"]):
                yield

    return _multi_patch()


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
class TestAddCommand:
    def _write_md(self, path, frontmatter, body="Some content."):
        """Helper to write a markdown file with frontmatter."""
        path.write_text(f"---\n{frontmatter}\n---\n\n{body}", encoding="utf-8")

    def test_add_valid_file(self, cli_env):
        md = cli_env["tmpdir"] / "test-add.md"
        self._write_md(md, "type: note\ntitle: Added Note\ntags:\n  - test")
        with _patch_config(cli_env):
            result = runner.invoke(app, ["add", str(md), "--kb", "test-events"])
            assert result.exit_code == 0
            assert "Added" in result.output
            assert "added-note" in result.output

    def test_add_validate_only(self, cli_env):
        md = cli_env["tmpdir"] / "test-validate.md"
        self._write_md(md, "type: note\ntitle: Validate Only Note")
        with _patch_config(cli_env):
            result = runner.invoke(
                app, ["add", str(md), "--kb", "test-events", "--validate-only"]
            )
            assert result.exit_code == 0
            assert "Valid" in result.output
            # Should NOT be saved to KB directory
            events_path = cli_env["events_kb"].path
            assert not (events_path / "notes" / "validate-only-note.md").exists()
            assert not (events_path / "validate-only-note.md").exists()

    def test_add_missing_type(self, cli_env):
        md = cli_env["tmpdir"] / "no-type.md"
        self._write_md(md, "title: No Type Here")
        with _patch_config(cli_env):
            result = runner.invoke(app, ["add", str(md), "--kb", "test-events"])
            assert result.exit_code == 1
            assert "type" in result.output.lower()

    def test_add_missing_title(self, cli_env):
        md = cli_env["tmpdir"] / "no-title.md"
        self._write_md(md, "type: note")
        with _patch_config(cli_env):
            result = runner.invoke(app, ["add", str(md), "--kb", "test-events"])
            assert result.exit_code == 1
            assert "title" in result.output.lower()

    def test_add_generates_id(self, cli_env):
        md = cli_env["tmpdir"] / "auto-id.md"
        self._write_md(md, "type: note\ntitle: Auto Generated ID")
        with _patch_config(cli_env):
            result = runner.invoke(app, ["add", str(md), "--kb", "test-events"])
            assert result.exit_code == 0
            assert "auto-generated-id" in result.output

    def test_add_nonexistent_file(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(
                app, ["add", "/tmp/does-not-exist-12345.md", "--kb", "test-events"]
            )
            assert result.exit_code == 1
            assert "not found" in result.output.lower() or "Error" in result.output

    def test_add_nonexistent_kb(self, cli_env):
        md = cli_env["tmpdir"] / "good-file.md"
        self._write_md(md, "type: note\ntitle: Good File")
        with _patch_config(cli_env):
            result = runner.invoke(app, ["add", str(md), "--kb", "nonexistent"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower() or "Error" in result.output

    def test_add_duplicate_id(self, cli_env):
        md = cli_env["tmpdir"] / "dup.md"
        self._write_md(md, "type: note\ntitle: Duplicate Entry")
        with _patch_config(cli_env):
            result = runner.invoke(app, ["add", str(md), "--kb", "test-events"])
            assert result.exit_code == 0
            # Add same file again
            result = runner.invoke(app, ["add", str(md), "--kb", "test-events"])
            assert result.exit_code == 1
            assert "already exists" in result.output.lower() or "Error" in result.output


@pytest.mark.cli
class TestCreateImprovements:
    def test_create_body_file(self, cli_env):
        body_path = cli_env["tmpdir"] / "body.txt"
        body_path.write_text("Body from file content.", encoding="utf-8")
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
                    "Body File Test",
                    "--body-file",
                    str(body_path),
                ],
            )
            assert result.exit_code == 0
            assert "Created" in result.output

    def test_create_stdin(self, cli_env):
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
                    "Stdin Test",
                    "--stdin",
                ],
                input="Body from stdin.",
            )
            assert result.exit_code == 0
            assert "Created" in result.output

    def test_create_template_note(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["create", "--template", "--type", "note"])
            assert result.exit_code == 0
            assert "---" in result.output
            assert "type: note" in result.output
            assert "Your Title Here" in result.output

    def test_create_template_event(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["create", "--template", "--type", "event"])
            assert result.exit_code == 0
            assert "type: event" in result.output
            assert "date:" in result.output or "location:" in result.output

    def test_create_template_no_title(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["create", "--template"])
            assert result.exit_code == 0
            assert "Your Title Here" in result.output

    def test_create_body_file_merges_frontmatter(self, cli_env):
        """Fields from file frontmatter appear in created entry metadata."""
        body_path = cli_env["tmpdir"] / "with_fm.md"
        body_path.write_text(
            "---\nkind: component\npath: src/foo.py\nowner: alice\n---\nActual body content.",
            encoding="utf-8",
        )
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "create",
                    "--kb", "test-events",
                    "--type", "note",
                    "--title", "FM Merge Test",
                    "--body-file", str(body_path),
                ],
            )
            assert result.exit_code == 0
            assert "Created" in result.output

            # Read back the saved file and verify frontmatter was merged
            saved = list(cli_env["events_kb"].path.glob("**/*fm-merge-test*"))
            assert len(saved) == 1
            content = saved[0].read_text(encoding="utf-8")
            assert "kind: component" in content
            assert "owner: alice" in content
            assert "path: src/foo.py" in content
            # Body should be just the content after closing ---
            assert "Actual body content." in content
            # Frontmatter block should NOT appear in body
            assert content.count("---") == 2  # only the entry's own frontmatter fences

    def test_create_body_file_cli_flags_override(self, cli_env):
        """Explicit CLI --field takes precedence over file frontmatter."""
        body_path = cli_env["tmpdir"] / "override.md"
        body_path.write_text(
            "---\nkind: from-file\npriority: low\n---\nOverride body.",
            encoding="utf-8",
        )
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "create",
                    "--kb", "test-events",
                    "--type", "note",
                    "--title", "Override Test",
                    "--body-file", str(body_path),
                    "--field", "kind=from-cli",
                ],
            )
            assert result.exit_code == 0

            saved = list(cli_env["events_kb"].path.glob("**/*override-test*"))
            assert len(saved) == 1
            content = saved[0].read_text(encoding="utf-8")
            assert "kind: from-cli" in content
            # priority from file should still be present
            assert "priority: low" in content

    def test_create_body_file_plain_content(self, cli_env):
        """File without frontmatter works as before (no regression)."""
        body_path = cli_env["tmpdir"] / "plain.txt"
        body_path.write_text("Just plain text, no frontmatter.", encoding="utf-8")
        with _patch_config(cli_env):
            result = runner.invoke(
                app,
                [
                    "create",
                    "--kb", "test-events",
                    "--type", "note",
                    "--title", "Plain Body Test",
                    "--body-file", str(body_path),
                ],
            )
            assert result.exit_code == 0
            assert "Created" in result.output

            saved = list(cli_env["events_kb"].path.glob("**/*plain-body-test*"))
            assert len(saved) == 1
            content = saved[0].read_text(encoding="utf-8")
            assert "Just plain text, no frontmatter." in content


@pytest.mark.cli
class TestTyperConfigCommand:
    def test_config_shows_info(self, cli_env):
        with _patch_config(cli_env):
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0
            assert "Config file" in result.output
