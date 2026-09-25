"""A KB added with `pyrite kb add` is found by every command in #363's repro.

`kb add` registers a KB in the index database and leaves config.yaml alone.
`get`, `index sync` and `link` build their config through the helpers in
`pyrite/cli/context.py`, which merge that registry. `search -k`, `kb validate`,
`kb schema ...` and `schema validate -k` called a bare `load_config()`, which
knows only config.yaml, so they answered KB_NOT_FOUND for the same KB.

These tests run the real CLI end to end: `kb add` and `index sync` against a
config and data dir in a temp directory (PYRITE_CONFIG_DIR / PYRITE_DATA_DIR),
then the command under test. Nothing patches `load_config`.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrite.cli import app

runner = CliRunner()

KB_NAME = "notes"


@pytest.fixture
def added_kb(tmp_path: Path, monkeypatch) -> Path:
    """A KB added with `pyrite kb add` and indexed, as in the issue's repro."""
    import pyrite.config as config_module

    home = tmp_path / "pyrite-home"
    home.mkdir()
    monkeypatch.setenv("PYRITE_CONFIG_DIR", str(home))
    monkeypatch.setenv("PYRITE_DATA_DIR", str(home))
    # CONFIG_DIR is resolved at import time; point it at the same temp dir.
    monkeypatch.setattr(config_module, "CONFIG_DIR", home)
    monkeypatch.setattr(config_module, "CONFIG_FILE", home / "config.yaml")

    kb_path = tmp_path / KB_NAME
    kb_path.mkdir()
    (kb_path / "kb.yaml").write_text(
        f"name: {KB_NAME}\nkb_type: generic\ntypes:\n  note:\n    description: A note\n",
        encoding="utf-8",
    )
    (kb_path / "hello.md").write_text(
        "---\nid: hello\ntitle: Hello\ntype: note\n---\n\nhello world\n", encoding="utf-8"
    )

    added = runner.invoke(app, ["kb", "add", str(kb_path), "--name", KB_NAME])
    assert added.exit_code == 0, added.output
    synced = runner.invoke(app, ["index", "sync"])
    assert synced.exit_code == 0, synced.output

    # The state the bug needs: the KB is in the database registry only.
    config_yaml = home / "config.yaml"
    assert not config_yaml.exists() or KB_NAME not in config_yaml.read_text(encoding="utf-8")
    return kb_path


def test_search_scoped_to_an_added_kb(added_kb):
    result = runner.invoke(app, ["search", "hello", "-k", KB_NAME, "--format", "json"])

    assert "KB_NOT_FOUND" not in result.output
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert [r["kb_name"] for r in data["results"]] == [KB_NAME]


def test_kb_validate_an_added_kb(added_kb):
    result = runner.invoke(app, ["kb", "validate", KB_NAME, "--format", "json"])

    assert "KB_NOT_FOUND" not in result.output
    assert result.exit_code == 0, result.output
    assert [kb["name"] for kb in json.loads(result.output)["kbs"]] == [KB_NAME]


def test_bare_kb_validate_includes_an_added_kb(added_kb):
    result = runner.invoke(app, ["kb", "validate", "--format", "json"])

    assert result.exit_code == 0, result.output
    assert KB_NAME in [kb["name"] for kb in json.loads(result.output)["kbs"]]


def test_kb_schema_show_an_added_kb(added_kb):
    result = runner.invoke(app, ["kb", "schema", "show", KB_NAME, "--format", "json"])

    assert "KB_NOT_FOUND" not in result.output
    assert result.exit_code == 0, result.output
    assert "note" in json.loads(result.output)["types"]


def test_schema_validate_an_added_kb(added_kb):
    result = runner.invoke(app, ["schema", "validate", "-k", KB_NAME])

    assert "KB_NOT_FOUND" not in result.output
    assert result.exit_code == 0, result.output


# `kb schema add-type`, `remove-type` and `set` are not in the issue's repro,
# but they sit on the same bare `load_config()` lines the issue lists, and
# these tests show they had the same bug.


def test_kb_schema_add_and_remove_type_on_an_added_kb(added_kb):
    added = runner.invoke(
        app, ["kb", "schema", "add-type", KB_NAME, "--type", "memo", "--format", "json"]
    )
    assert added.exit_code == 0, added.output
    assert "memo" in (added_kb / "kb.yaml").read_text(encoding="utf-8")

    removed = runner.invoke(
        app, ["kb", "schema", "remove-type", KB_NAME, "--type", "memo", "--format", "json"]
    )
    assert removed.exit_code == 0, removed.output
    assert "memo" not in (added_kb / "kb.yaml").read_text(encoding="utf-8")


def test_kb_schema_set_on_an_added_kb(added_kb, tmp_path):
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("types:\n  memo:\n    description: A memo\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["kb", "schema", "set", KB_NAME, "--schema-file", str(schema_file), "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    assert "memo" in (added_kb / "kb.yaml").read_text(encoding="utf-8")


def test_an_unknown_kb_still_reports_kb_not_found(added_kb):
    """Guard: merging the registry must not make every name resolve."""
    for args in (
        ["search", "hello", "-k", "nope", "--format", "json"],
        ["kb", "validate", "nope", "--format", "json"],
        ["kb", "schema", "show", "nope", "--format", "json"],
        ["schema", "validate", "-k", "nope"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code != 0, (args, result.output)
        assert "KB_NOT_FOUND" in result.output or "not found" in result.output, (
            args,
            result.output,
        )
