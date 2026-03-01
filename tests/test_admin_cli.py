"""Tests for admin CLI commands: kb, index, qa, schema, extension.

Tests the CLI command groups not covered by test_cli_commands.py (which covers
get, create, update, delete, list, timeline, tags, backlinks, config).
Uses CliRunner with patched config.
"""

import contextlib
import tempfile
from pathlib import Path
from unittest.mock import patch

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
def admin_env():
    """Environment for admin CLI tests."""
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
            description="Test events KB",
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

        yield {
            "config": config,
            "tmpdir": tmpdir,
            "events_kb": events_kb,
            "research_kb": research_kb,
        }


@contextlib.contextmanager
def _patch_config(env):
    """Patch load_config at the source so all importers see it."""
    target = env["config"]
    with (
        patch("pyrite.config.load_config", return_value=target),
        patch("pyrite.cli.load_config", return_value=target),
        patch("pyrite.cli.context.load_config", return_value=target),
        patch("pyrite.cli.kb_commands.load_config", return_value=target),
        patch("pyrite.cli.search_commands.load_config", return_value=target),
    ):
        yield


# =========================================================================
# KB commands
# =========================================================================


@pytest.mark.cli
class TestKBList:
    def test_kb_list(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "list"])
            assert result.exit_code == 0
            assert "test-events" in result.output

    def test_kb_list_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "list", "--format", "json"])
            assert result.exit_code == 0
            data = _parse_json(result.output)
            assert isinstance(data, (list, dict))


@pytest.mark.cli
class TestKBDiscover:
    def test_kb_discover(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "discover", str(admin_env["tmpdir"])])
            assert result.exit_code == 0

    def test_kb_discover_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "discover", str(admin_env["tmpdir"]), "--format", "json"])
            assert result.exit_code == 0


@pytest.mark.cli
class TestKBValidate:
    def test_kb_validate(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "validate"])
            assert result.exit_code in (0, 1)

    def test_kb_validate_specific_kb(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "validate", "test-events"])
            # Exit 0 = valid, exit 1 = validation errors (both are non-crash)
            assert result.exit_code in (0, 1)

    def test_kb_validate_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["kb", "validate", "--format", "json"])
            assert result.exit_code in (0, 1)


# =========================================================================
# Index commands
# =========================================================================


@pytest.mark.cli
class TestIndexBuild:
    def test_index_build(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "build"])
            assert result.exit_code == 0
            assert "entries" in result.output.lower() or "build complete" in result.output.lower()


@pytest.mark.cli
class TestIndexSync:
    def test_index_sync(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "sync"])
            assert result.exit_code == 0
            assert "Sync complete" in result.output

    def test_index_sync_specific_kb(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "sync", "test-events"])
            assert result.exit_code == 0


@pytest.mark.cli
class TestIndexStats:
    def test_index_stats(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "stats"])
            assert result.exit_code == 0

    def test_index_stats_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "stats", "--format", "json"])
            assert result.exit_code == 0
            data = _parse_json(result.output)
            assert "total_entries" in data or "entries" in str(data).lower()


@pytest.mark.cli
class TestIndexHealth:
    def test_index_health(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "health"])
            assert result.exit_code == 0

    def test_index_health_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["index", "health", "--format", "json"])
            assert result.exit_code == 0
            data = _parse_json(result.output)
            assert isinstance(data, dict)


# =========================================================================
# QA commands
# =========================================================================


@pytest.mark.cli
class TestQAValidate:
    def test_qa_validate(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["qa", "validate"])
            assert result.exit_code == 0

    def test_qa_validate_specific_kb(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["qa", "validate", "test-events"])
            assert result.exit_code == 0

    def test_qa_validate_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["qa", "validate", "--format", "json"])
            assert result.exit_code == 0
            data = _parse_json(result.output)
            assert isinstance(data, (list, dict))


@pytest.mark.cli
class TestQAStatus:
    def test_qa_status(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["qa", "status"])
            assert result.exit_code == 0

    def test_qa_status_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["qa", "status", "--format", "json"])
            assert result.exit_code == 0


# =========================================================================
# Search command
# =========================================================================


@pytest.mark.cli
class TestSearchCommand:
    def test_search_finds_entries(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["search", "immigration"])
            assert result.exit_code == 0
            assert "Test Event" in result.output or "immigration" in result.output.lower()

    def test_search_no_results(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["search", "xyznonexistent123"])
            assert result.exit_code == 0

    def test_search_with_kb_filter(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["search", "immigration", "--kb", "test-events"])
            assert result.exit_code == 0


# =========================================================================
# Extension commands
# =========================================================================


@pytest.mark.cli
class TestExtensionList:
    def test_extension_list(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["extension", "list"])
            # May have plugins or not — should not crash
            assert result.exit_code == 0

    def test_extension_list_json(self, admin_env):
        with _patch_config(admin_env):
            result = runner.invoke(app, ["extension", "list", "--format", "json"])
            assert result.exit_code == 0


@pytest.mark.cli
class TestExtensionInit:
    def test_extension_init(self, admin_env):
        ext_path = admin_env["tmpdir"] / "test-ext"
        with _patch_config(admin_env):
            result = runner.invoke(app, ["extension", "init", "test-ext", "--path", str(ext_path)])
            assert result.exit_code == 0
            assert (ext_path / "pyproject.toml").exists()

    def test_extension_init_with_types(self, admin_env):
        ext_path = admin_env["tmpdir"] / "typed-ext"
        with _patch_config(admin_env):
            result = runner.invoke(
                app,
                ["extension", "init", "typed-ext", "--path", str(ext_path), "--types", "widget,gadget"],
            )
            assert result.exit_code == 0
            assert (ext_path / "pyproject.toml").exists()


# =========================================================================
# Init command (headless KB creation)
# =========================================================================


@pytest.mark.cli
class TestInitCommand:
    def test_init_creates_kb(self, admin_env):
        kb_path = admin_env["tmpdir"] / "new-kb"
        with _patch_config(admin_env):
            result = runner.invoke(app, ["init", "--path", str(kb_path), "--template", "empty"])
            assert result.exit_code == 0
            assert (kb_path / "kb.yaml").exists()

    def test_init_with_template(self, admin_env):
        kb_path = admin_env["tmpdir"] / "software-kb"
        with _patch_config(admin_env):
            result = runner.invoke(app, ["init", "--path", str(kb_path), "--template", "software"])
            assert result.exit_code == 0


# =========================================================================
# Helpers
# =========================================================================


import json


def _parse_json(output: str) -> dict | list:
    """Parse JSON from CLI output, handling potential non-JSON prefix lines."""
    # Try full output first
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        pass
    # Try last line (some commands print header + JSON)
    for line in reversed(output.strip().split("\n")):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    # Try finding JSON object/array in output
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = output.find(start_char)
        if start >= 0:
            end = output.rfind(end_char)
            if end > start:
                try:
                    return json.loads(output[start : end + 1])
                except json.JSONDecodeError:
                    continue
    pytest.fail(f"Could not parse JSON from output: {output[:200]}")
