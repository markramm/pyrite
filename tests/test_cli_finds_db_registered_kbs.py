"""CLI regressions for knowledge bases registered by `pyrite kb add`.

Issue #363: commands that load only config.yaml must also resolve KBs stored
in the index database. These tests use isolated config and data directories and
invoke the real Typer commands against SQLite.
"""

import json

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.storage.database import PyriteDB

runner = CliRunner()


@pytest.fixture
def registered_kb(tmp_path, monkeypatch):
    import pyrite.config as config_module

    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    kb_path = tmp_path / "kb"
    config_dir.mkdir()
    data_dir.mkdir()
    kb_path.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("knowledge_bases: []\nsettings: {}\n", encoding="utf-8")
    (kb_path / "kb.yaml").write_text(
        "name: registry-only\ntypes:\n  note:\n    required: [title]\n",
        encoding="utf-8",
    )
    entry = kb_path / "entry.md"
    entry.write_text(
        "---\ntype: note\ntitle: Registered entry\n---\n\n"
        "A distinctive pineapple-search-token appears here.\n",
        encoding="utf-8",
    )

    # Config resolves its directory at import time; keep the test's explicit
    # environment and the module constants aligned.
    monkeypatch.setenv("PYRITE_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("PYRITE_DATA_DIR", str(data_dir))
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

    db = PyriteDB(data_dir / "index.db")
    db.register_kb(
        name="registry-only",
        kb_type="generic",
        path=str(kb_path),
        description="Registered from the CLI",
        source="user",
    )
    db.close()

    return {
        "config_dir": config_dir,
        "config_file": config_file,
        "data_dir": data_dir,
        "kb_path": kb_path,
        "entry": entry,
    }


def _invoke(args: list[str]):
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return result


def test_search_finds_db_registered_kb(registered_kb):
    result = _invoke(
        ["search", "pineapple-search-token", "-k", "registry-only", "--format", "json"]
    )

    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["results"][0]["kb_name"] == "registry-only"


def test_kb_validate_finds_named_db_registered_kb(registered_kb):
    payload = json.loads(_invoke(["kb", "validate", "registry-only", "--format", "json"]).stdout)

    assert [kb["name"] for kb in payload["kbs"]] == ["registry-only"]


def test_kb_validate_without_name_includes_db_registered_kbs(registered_kb):
    payload = json.loads(_invoke(["kb", "validate", "--format", "json"]).stdout)

    assert [kb["name"] for kb in payload["kbs"]] == ["registry-only"]


def test_kb_schema_show_finds_db_registered_kb(registered_kb):
    payload = json.loads(
        _invoke(["kb", "schema", "show", "registry-only", "--format", "json"]).stdout
    )

    assert payload["kb_name"] == "registry-only"
    assert "note" in payload["types"]


def test_schema_validate_finds_db_registered_kb(registered_kb):
    result = _invoke(["schema", "validate", "--kb", "registry-only"])

    assert "1 files" in result.output
    assert "0 errors" in result.output


def test_kb_schema_add_type_finds_db_registered_kb(registered_kb):
    payload = json.loads(
        _invoke(
            [
                "kb",
                "schema",
                "add-type",
                "registry-only",
                "--type",
                "project",
                "--format",
                "json",
            ]
        ).stdout
    )

    assert payload["added"] is True
    assert payload["type_name"] == "project"


def test_kb_schema_remove_type_finds_db_registered_kb(registered_kb):
    payload = json.loads(
        _invoke(
            [
                "kb",
                "schema",
                "remove-type",
                "registry-only",
                "--type",
                "note",
                "--format",
                "json",
            ]
        ).stdout
    )

    assert payload["removed"] is True


def test_kb_schema_set_finds_db_registered_kb(registered_kb, tmp_path):
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text(
        "types:\n  project:\n    required: [title]\n",
        encoding="utf-8",
    )

    payload = json.loads(
        _invoke(
            [
                "kb",
                "schema",
                "set",
                "registry-only",
                "--schema-file",
                str(schema_file),
                "--format",
                "json",
            ]
        ).stdout
    )

    assert payload["set"] is True
    assert payload["type_count"] == 1


@pytest.mark.control(
    reason="YAML-configured KBs keep precedence over same-named database registrations."
)
def test_yaml_config_kb_keeps_precedence_over_db_registration(registered_kb, tmp_path):
    import json as json_module

    from pyrite.cli.context import get_config_and_db

    yaml_kb_path = tmp_path / "yaml-kb"
    yaml_kb_path.mkdir()
    registered_kb["config_file"].write_text(
        json_module.dumps(
            {
                "knowledge_bases": [
                    {
                        "name": "registry-only",
                        "path": str(yaml_kb_path),
                        "kb_type": "generic",
                    }
                ],
                "settings": {},
            }
        ),
        encoding="utf-8",
    )

    config, db = get_config_and_db()
    try:
        assert config.get_kb("registry-only").path == yaml_kb_path.resolve()
        assert [kb.name for kb in config.all_kbs()] == ["registry-only"]
    finally:
        db.close()
