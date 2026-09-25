"""`pyrite task create --field key=value` (#397).

`task create` had no way to supply a kb.yaml-required field, so a KB that
requires fields on `task` (the desk schema requires `project` and `kind`)
could not create a task through this command at all -- validation refused
the create and there was no option to satisfy it. `-f` is already
`--format` on the task commands (#303), so this is `--field` only, with no
short flag, matching `create`/`update`'s parser (`_parse_field_value`).

`--field` is refused for any key that already has its own option (`title`,
`body`, `parent`, `priority`, `assignee`, `tags`), for `status` (task
lifecycle is `task update --status`, not a free-form field), and for a
task's `managed_fields` (`status_change_log`, `evidence`, `agent_context`,
`assigned_at`) -- `create` does not run the managed-field refusal that
`update` does, so without this the audit trail could be forged at creation.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB
from pyrite.utils.yaml import load_yaml

runner = CliRunner()

DESK_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "docs" / "desk-schema.yaml"


def _task_frontmatter(config: PyriteConfig, kb_name: str, entry_id: str, subdir: str) -> dict:
    tasks_path = config.get_kb(kb_name).path
    content = (tasks_path / subdir / f"{entry_id}.md").read_text(encoding="utf-8")
    return load_yaml(content.split("---", 2)[1])


@pytest.fixture
def desk_env(tmp_path):
    """A KB initialised from the real `docs/desk-schema.yaml`, the schema the
    conductor-desk recipe actually uses -- required fields `project` and
    `kind` on `task`."""
    desk_path = tmp_path / "desk"
    (desk_path / "tasks").mkdir(parents=True)
    (desk_path / "kb.yaml").write_text(DESK_SCHEMA_PATH.read_text(encoding="utf-8"))
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-desk", path=desk_path, kb_type="task")],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(config.settings.index_path)
    db.register_kb(name="test-desk", kb_type="task", path=str(desk_path), description="desk")
    db.close()
    with patch("pyrite.cli.context.load_config", return_value=config):
        yield {"config": config}


@pytest.fixture
def task_cli_env(tmp_path):
    tasks_path = tmp_path / "tasks-kb"
    (tasks_path / "tasks").mkdir(parents=True)
    kb_config = KBConfig(
        name="test-tasks", path=tasks_path, kb_type="task", description="Test task KB"
    )
    config = PyriteConfig(
        knowledge_bases=[kb_config],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(config.settings.index_path)
    db.register_kb(
        name="test-tasks", kb_type="task", path=str(tasks_path), description="Test task KB"
    )
    db.close()
    with patch("pyrite.cli.context.load_config", return_value=config):
        yield {"config": config}


@pytest.mark.cli
@pytest.mark.control(
    reason="the schema refusal without --field already worked before #397; "
    "this pins the baseline the rest of the file's tests build on"
)
def test_task_create_with_field_satisfies_required_schema_fields(desk_env):
    """Without --field, the desk schema's required fields refuse the create."""
    result = runner.invoke(
        app, ["task", "create", "Try it", "-k", "test-desk", "-b", "desc", "--format", "json"]
    )
    assert result.exit_code != 0
    assert "project" in result.output and "kind" in result.output


@pytest.mark.cli
def test_task_create_with_field_creates_the_task(desk_env):
    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "Try it",
            "-k",
            "test-desk",
            "-b",
            "desc",
            "--field",
            "project=demo",
            "--field",
            "kind=note",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    fm = _task_frontmatter(desk_env["config"], "test-desk", data["entry_id"], "tasks")
    assert fm["project"] == "demo"
    assert fm["kind"] == "note"


@pytest.mark.cli
def test_conductor_desk_recipe_creates_a_task_in_one_step(desk_env):
    """`docs/conductor-desk.md`'s one-step recipe: title, --priority, --body,
    --tags and the desk schema's required --field project/kind, all on one
    `task create` call, against the real desk schema."""
    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "Merge #184",
            "-k",
            "test-desk",
            "--priority",
            "3",
            "-b",
            "Recommendation and link...",
            "--tags",
            "outside,quick",
            "--field",
            "project=demo",
            "--field",
            "kind=merge",
            "--field",
            "link=https://example.com/pr/184",
            "--field",
            "requested_by=conductor",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    fm = _task_frontmatter(desk_env["config"], "test-desk", data["entry_id"], "tasks")
    assert fm["project"] == "demo"
    assert fm["kind"] == "merge"
    assert fm["link"] == "https://example.com/pr/184"
    assert fm["requested_by"] == "conductor"
    assert fm["tags"] == ["outside", "quick"]
    assert fm["priority"] == 3


@pytest.mark.cli
def test_task_create_field_uses_the_shared_value_parser(task_cli_env):
    """`--field tags=a,b` parses through `_parse_field_value`, like `create`/`update`."""
    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "Parsed",
            "-k",
            "test-tasks",
            "--field",
            "custom_list=a,b",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    fm = _task_frontmatter(task_cli_env["config"], "test-tasks", data["entry_id"], "tasks")
    assert fm["custom_list"] == ["a", "b"], fm


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        # Without --field at all (pre-#397), typer's own "no such option"
        # usage banner happens to contain the word "TITLE" (from
        # `[OPTIONS] [TITLE]`), so this case passes by coincidence even
        # without the fix -- unlike the others, whose flag name never
        # appears in that generic banner.
        pytest.param(
            "title",
            "dup title",
            marks=pytest.mark.control(
                reason="typer's usage banner contains the word 'TITLE' regardless of --field"
            ),
        ),
        ("body", "dup body"),
        ("parent", "some-parent"),
        ("priority", "3"),
        ("assignee", "agent:x"),
        ("tags", "a,b"),
    ],
)
@pytest.mark.cli
def test_task_create_field_refuses_a_key_with_its_own_option(task_cli_env, flag, value):
    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "T",
            "-k",
            "test-tasks",
            "--field",
            f"{flag}={value}",
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert flag in result.output.lower()


@pytest.mark.cli
def test_task_create_field_refuses_status(task_cli_env):
    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "T",
            "-k",
            "test-tasks",
            "--field",
            "status=blocked",
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert "status" in result.output.lower()


@pytest.mark.parametrize(
    "managed_field",
    ["status_change_log", "evidence", "agent_context", "assigned_at"],
)
@pytest.mark.cli
def test_task_create_field_refuses_managed_fields(task_cli_env, managed_field):
    result = runner.invoke(
        app,
        [
            "task",
            "create",
            "T",
            "-k",
            "test-tasks",
            "--field",
            f"{managed_field}=forged",
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert managed_field in result.output.lower()


@pytest.mark.cli
def test_task_create_help_lists_field_option():
    result = runner.invoke(app, ["task", "create", "--help"])
    assert result.exit_code == 0, result.stdout
    import re

    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", result.stdout)
    assert "--field" in clean
