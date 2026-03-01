"""Tests for CLI --format json output across all command groups.

Verifies that commands with --format json return valid JSON with expected keys.
"""

import json
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
def cli_env():
    """Environment for CLI JSON output tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        events_path = tmpdir / "events"
        events_path.mkdir()

        events_kb = KBConfig(name="test-events", path=events_path, kb_type=KBType.EVENTS)
        config = PyriteConfig(
            knowledge_bases=[events_kb],
            settings=Settings(index_path=db_path),
        )

        # Create sample data
        events_repo = KBRepository(events_kb)
        event = EventEntry.create(
            date="2025-01-10", title="Test Event", body="Body text.", importance=5
        )
        event.tags = ["test"]
        events_repo.save(event)

        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()
        db.close()

        yield {"config": config, "tmpdir": tmpdir}


def _patch_config(module_path, cli_env):
    """Patch load_config in both the given module and cli_context.

    After the cli_context refactor, commands that go through cli_context
    call load_config from pyrite.cli.context, not from their own module.
    We patch both locations to keep tests working.
    """
    import contextlib

    @contextlib.contextmanager
    def _multi_patch():
        # Always patch the context module (used by all refactored commands)
        with patch("pyrite.cli.context.load_config", return_value=cli_env["config"]):
            # Also patch the original module path (may no longer exist for some
            # modules after refactoring, so guard with a try/except)
            try:
                with patch(module_path, return_value=cli_env["config"]):
                    yield
            except AttributeError:
                yield

    return _multi_patch()


@pytest.mark.cli
def test_kb_list_json(cli_env):
    """kb list --format json returns valid JSON with 'kbs' key."""
    with _patch_config("pyrite.cli.kb_commands.load_config", cli_env):
        result = runner.invoke(app, ["kb", "list", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "kbs" in data
    assert isinstance(data["kbs"], list)
    assert len(data["kbs"]) > 0
    assert "name" in data["kbs"][0]


@pytest.mark.cli
def test_kb_discover_json(cli_env):
    """kb discover --format json returns valid JSON with 'discovered' key."""
    # Create a kb.yaml in the tmpdir so discover finds something
    kb_yaml = cli_env["tmpdir"] / "events" / "kb.yaml"
    kb_yaml.write_text("name: discovered-kb\ntype: events\n")

    with _patch_config("pyrite.cli.kb_commands.load_config", cli_env):
        result = runner.invoke(
            app, ["kb", "discover", str(cli_env["tmpdir"]), "--format", "json"]
        )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "discovered" in data
    assert isinstance(data["discovered"], list)


@pytest.mark.cli
def test_kb_validate_json(cli_env):
    """kb validate --format json returns valid JSON with 'kbs' and 'all_valid' keys."""
    with _patch_config("pyrite.cli.kb_commands.load_config", cli_env):
        result = runner.invoke(app, ["kb", "validate", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "kbs" in data
    assert "all_valid" in data
    assert isinstance(data["kbs"], list)


@pytest.mark.cli
def test_index_stats_json(cli_env):
    """index stats --format json returns valid JSON with 'total_entries' key."""
    with _patch_config("pyrite.cli.index_commands.load_config", cli_env):
        result = runner.invoke(app, ["index", "stats", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "total_entries" in data


@pytest.mark.cli
def test_index_health_json(cli_env):
    """index health --format json returns valid JSON with 'status' key."""
    with _patch_config("pyrite.cli.index_commands.load_config", cli_env):
        result = runner.invoke(app, ["index", "health", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "status" in data
    assert data["status"] in ("healthy", "unhealthy")


@pytest.mark.cli
def test_repo_list_json(cli_env):
    """repo list --format json returns valid JSON with 'repos' key."""
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    mock_repo_service = MagicMock()
    mock_user_service = MagicMock()
    mock_repo_service.list_repos.return_value = [
        {
            "id": 1,
            "name": "test-repo",
            "local_path": "/tmp/test",
            "remote_url": "https://github.com/test/test",
            "is_fork": False,
            "last_synced": None,
        }
    ]

    with patch(
        "pyrite.cli.repo_commands._get_db_and_services",
        return_value=(cli_env["config"], mock_db, mock_repo_service, mock_user_service),
    ):
        result = runner.invoke(app, ["repo", "list", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "repos" in data


@pytest.mark.cli
def test_qa_validate_json(cli_env):
    """qa validate --format json returns valid JSON with 'issues' key."""
    with _patch_config("pyrite.cli.qa_commands.load_config", cli_env):
        result = runner.invoke(
            app, ["qa", "validate", "test-events", "--format", "json"]
        )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "issues" in data
    assert "count" in data


@pytest.mark.cli
def test_qa_status_json(cli_env):
    """qa status --format json returns valid JSON."""
    with _patch_config("pyrite.cli.qa_commands.load_config", cli_env):
        result = runner.invoke(app, ["qa", "status", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "total_entries" in data or "total_issues" in data


@pytest.mark.cli
def test_auth_status_json(cli_env):
    """auth status --format json returns valid JSON with 'authenticated' key."""
    with (
        _patch_config("pyrite.cli.load_config", cli_env),
        patch(
            "pyrite.github_auth.check_github_auth",
            return_value=(True, "Authenticated via token"),
        ),
    ):
        result = runner.invoke(app, ["auth", "status", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "authenticated" in data
    assert data["authenticated"] is True


@pytest.mark.cli
def test_auth_whoami_json(cli_env):
    """auth whoami --format json returns valid JSON."""
    with (
        _patch_config("pyrite.cli.load_config", cli_env),
        patch("pyrite.services.user_service.UserService.get_current_user") as mock_user,
    ):
        mock_user.return_value = {
            "github_id": 12345,
            "github_login": "testuser",
            "display_name": "Test User",
            "email": "test@example.com",
        }
        result = runner.invoke(app, ["auth", "whoami", "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "github_login" in data or "github_id" in data
