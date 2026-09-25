"""CLI commands that #380 moved off direct DB access, characterized first.

Each test drives the real Typer app against a temporary index and pins
what the command prints or returns, so the move behind services is
checked against behaviour rather than against the diff.
"""

import contextlib
import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models.core_types import NoteEntry
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager

runner = CliRunner()


def _config(tmp_path, *, indexed=True):
    kb_path = tmp_path / "notes"
    kb_path.mkdir()
    for i in range(2):
        NoteEntry(id=f"n{i}", title=f"Note {i}", body=f"body {i}").save(kb_path / f"n{i}.md")
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="notes", path=kb_path, kb_type=KBType.GENERIC)],
        settings=Settings(index_path=tmp_path / "index.db", workspace_path=tmp_path / "ws"),
    )
    if indexed:
        db = PyriteDB(config.settings.index_path)
        IndexManager(db, config).index_all()
        db.close()
    return config


@contextlib.contextmanager
def _patched(config):
    with contextlib.ExitStack() as stack:
        for target in (
            "pyrite.config.load_config",
            "pyrite.cli.load_config",
            "pyrite.cli.context.load_config",
            "pyrite.cli.repo_commands.load_config",
            "pyrite.cli.search_commands.load_config",
            "pyrite.admin_cli.load_config",
        ):
            stack.enter_context(patch(target, return_value=config))
        yield


@pytest.fixture
def config(tmp_path):
    return _config(tmp_path)


@pytest.fixture
def repo_config(config):
    """A subscribed repo holding the `notes` KB."""
    db = PyriteDB(config.settings.index_path)
    repo = db.register_repo("org/notes", str(config.knowledge_bases[0].path))
    db.link_kb_to_repo("notes", repo["id"], "")
    db.close()
    return config


class TestRepoCommands:
    def test_repo_status_rich_lists_kbs_with_entry_counts(self, repo_config):
        from pyrite.cli import app

        with _patched(repo_config):
            result = runner.invoke(app, ["repo", "status", "org/notes", "--format", "rich"])
        assert result.exit_code == 0, result.output
        assert "KBs: 1" in result.output
        assert "- notes (2 entries)" in result.output

    def test_repo_list_rich_counts_kbs(self, repo_config):
        from pyrite.cli import app

        with _patched(repo_config):
            result = runner.invoke(app, ["repo", "list", "--format", "rich"])
        assert result.exit_code == 0, result.output
        row = next(line for line in result.output.splitlines() if "org/notes" in line)
        assert row.rstrip(" │|").split()[-1] == "1"

    def test_repo_status_json_shape(self, repo_config):
        from pyrite.cli import app

        with _patched(repo_config):
            result = runner.invoke(app, ["repo", "status", "org/notes", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["kb_names"] == ["notes"]
        assert data["total_entries"] == 2


class TestQAAndExport:
    def test_qa_checkers_kb_coverage_lists_entry_types(self, config):
        from pyrite.cli import app

        # Every type gets a one-item rubric, so each entry type the KB holds
        # prints a "Type:" header -- which is what the type query decides.
        with (
            _patched(config),
            patch(
                "pyrite.schema.core_types.resolve_type_metadata",
                return_value={"evaluation_rubric": ["judge me"]},
            ),
        ):
            result = runner.invoke(app, ["qa", "checkers", "--kb", "notes"])
        assert result.exit_code == 0, result.output
        assert [line for line in result.output.splitlines() if line.startswith("Type:")] == [
            "Type: note (1 items):"
        ]

    def test_qa_checkers_unknown_kb(self, config):
        from pyrite.cli import app

        with _patched(config):
            result = runner.invoke(app, ["qa", "checkers", "--kb", "nope"])
        assert result.exit_code == 1
        assert "KB 'nope' not found" in result.output

    def test_export_site_writes_every_entry(self, config, tmp_path):
        from pyrite.cli import app

        out = tmp_path / "site"
        with _patched(config):
            result = runner.invoke(app, ["export", "site", "-k", "notes", "-o", str(out)])
        assert result.exit_code == 0, result.output
        written = sorted(p.name for p in out.rglob("*.md"))
        assert any("n0" in n or "note-0" in n for n in written), written
        assert any("n1" in n or "note-1" in n for n in written), written


class TestSearchAndIndex:
    def test_search_on_an_empty_index_builds_it_first(self, tmp_path):
        from pyrite.cli import app

        config = _config(tmp_path, indexed=False)
        with _patched(config):
            result = runner.invoke(app, ["search", "body", "--format", "json"])
        assert result.exit_code == 0, result.output
        db = PyriteDB(config.settings.index_path)
        try:
            assert db.count_entries() == 2
        finally:
            db.close()

    def test_index_embed_refuses_an_empty_index(self, tmp_path):
        from pyrite.services.embedding_service import is_available

        config = _config(tmp_path, indexed=False)
        db = PyriteDB(config.settings.index_path)
        vec = db.vec_available
        db.close()
        if not (is_available() and vec):
            pytest.skip("semantic extras not installed: the empty-index check is not reached")
        from pyrite.cli import app

        with _patched(config):
            result = runner.invoke(app, ["index", "embed"])
        assert result.exit_code != 0
        assert "INDEX_EMPTY" in result.output or "Index is empty" in result.output


class TestAdminCli:
    """`pyrite-admin` (admin_cli.py) index and auth commands."""

    def test_index_build_stats_sync_health(self, tmp_path):
        from pyrite.admin_cli import app

        config = _config(tmp_path, indexed=False)
        with _patched(config):
            build = runner.invoke(app, ["index", "build"])
            stats = runner.invoke(app, ["index", "stats"])
            sync = runner.invoke(app, ["index", "sync"])
            health = runner.invoke(app, ["index", "health"])
            one = runner.invoke(app, ["index", "build", "notes"])
        assert build.exit_code == 0, build.output
        assert "Indexed 2 entries across 1 KBs" in build.output
        assert "Total entries:" in stats.output and "2" in stats.output
        assert sync.exit_code == 0 and "Synced:" in sync.output
        assert health.exit_code == 0 and "Index is healthy." in health.output
        assert "Indexed 2 entries from notes" in one.output

    def test_auth_whoami_local(self, config):
        from pyrite.admin_cli import app

        with _patched(config):
            result = runner.invoke(app, ["auth", "whoami"])
        assert result.exit_code == 0, result.output
        assert "Identity: local" in result.output

    def test_repo_sync_unknown(self, config):
        from pyrite.admin_cli import app

        with _patched(config):
            result = runner.invoke(app, ["repo", "sync", "org/none"])
        assert "org/none" in result.output or "not found" in result.output.lower()
