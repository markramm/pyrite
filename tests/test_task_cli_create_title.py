"""CLI tests for `pyrite task create` title ergonomics.

Regression coverage for
`bug-task-create-title-is-positional-while-body-priority-are-flags-inconsistent-cli`:
title was positional-only while body/priority/parent were flags, so
`task create --title X --body Y` failed with "No such option: --title".

Fix: accept the title EITHER as a positional argument OR via `--title`,
so both invocation styles work. Supplying neither (or both) is a clear error.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

runner = CliRunner()


@pytest.fixture
def task_cli_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tasks_path = tmpdir / "tasks-kb"
        (tasks_path / "tasks").mkdir(parents=True)
        kb_config = KBConfig(
            name="test-tasks", path=tasks_path, kb_type="task", description="Test task KB"
        )
        config = PyriteConfig(
            knowledge_bases=[kb_config],
            settings=Settings(index_path=tmpdir / "index.db"),
        )
        db = PyriteDB(config.settings.index_path)
        db.register_kb(
            name="test-tasks", kb_type="task", path=str(tasks_path), description="Test task KB"
        )
        db.close()
        with patch("pyrite.cli.task_commands.load_config", return_value=config):
            yield {"config": config}


@pytest.mark.cli
def test_task_create_with_positional_title(task_cli_env):
    """The original positional form still works."""
    result = runner.invoke(
        app, ["task", "create", "Positional title", "-k", "test-tasks", "-f", "json"]
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["title"] == "Positional title"


@pytest.mark.cli
def test_task_create_with_title_flag(task_cli_env):
    """`--title` flag now works as an alternative to the positional argument."""
    result = runner.invoke(
        app, ["task", "create", "--title", "Flag title", "-k", "test-tasks", "-f", "json"]
    )
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert data["title"] == "Flag title"


@pytest.mark.cli
def test_task_create_missing_title_is_clear_error(task_cli_env):
    """Supplying no title at all fails with a helpful message, not a crash."""
    result = runner.invoke(app, ["task", "create", "-k", "test-tasks"])
    assert result.exit_code != 0
    assert "title" in (result.stdout + result.stderr).lower()
