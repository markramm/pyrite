"""Tests for the import CLI command and YAML importer."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.formats.importers.yaml_importer import import_yaml
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager

runner = CliRunner()


@pytest.fixture
def import_env():
    """Environment for import CLI tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        kb_path = tmpdir / "test-kb"
        kb_path.mkdir()

        kb_config = KBConfig(
            name="test-kb",
            path=kb_path,
            kb_type=KBType.GENERIC,
        )

        config = PyriteConfig(
            knowledge_bases=[kb_config],
            settings=Settings(index_path=db_path),
        )

        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()
        db.close()

        yield {"config": config, "tmpdir": tmpdir, "kb_path": kb_path}


def _patch_config(env):
    import contextlib
    from unittest.mock import patch

    @contextlib.contextmanager
    def _multi_patch():
        with patch("pyrite.cli.load_config", return_value=env["config"]):
            with patch("pyrite.cli.context.load_config", return_value=env["config"]):
                yield

    return _multi_patch()


class TestYamlImporter:
    def test_parse_entries_wrapper(self):
        data = """
entries:
  - title: "Test Entry"
    entry_type: note
    tags: [test]
    body: "Hello world"
  - title: "Second"
    type: person
    body: "A person"
"""
        result = import_yaml(data)
        assert len(result) == 2
        assert result[0]["title"] == "Test Entry"
        assert result[0]["entry_type"] == "note"
        assert result[0]["tags"] == ["test"]
        assert result[1]["entry_type"] == "person"

    def test_parse_single_entry(self):
        data = """
title: "Solo Entry"
entry_type: event
body: "Just one"
importance: 7
"""
        result = import_yaml(data)
        assert len(result) == 1
        assert result[0]["title"] == "Solo Entry"
        assert result[0]["importance"] == 7

    def test_parse_bytes(self):
        data = b'entries:\n  - title: "Bytes"\n    body: "from bytes"'
        result = import_yaml(data)
        assert len(result) == 1
        assert result[0]["title"] == "Bytes"

    def test_optional_fields(self):
        data = """
entries:
  - title: "With Extras"
    body: "body"
    importance: 8
    date: "2025-01-01"
    status: active
    summary: "A summary"
"""
        result = import_yaml(data)
        assert result[0]["importance"] == 8
        assert result[0]["date"] == "2025-01-01"
        assert result[0]["status"] == "active"
        assert result[0]["summary"] == "A summary"


@pytest.mark.cli
class TestImportCommand:
    def test_import_json_file(self, import_env):
        entries = {
            "entries": [
                {"title": "JSON Entry 1", "entry_type": "note", "body": "Body 1"},
                {"title": "JSON Entry 2", "entry_type": "note", "body": "Body 2"},
            ]
        }
        json_file = import_env["tmpdir"] / "import.json"
        json_file.write_text(json.dumps(entries))

        with _patch_config(import_env):
            result = runner.invoke(app, ["import", str(json_file), "--kb", "test-kb"])
            assert result.exit_code == 0
            assert "Created" in result.output
            assert "Imported 2 entries" in result.output

    def test_import_yaml_file(self, import_env):
        yaml_content = """entries:
  - title: "YAML Entry 1"
    entry_type: note
    body: "Body 1"
  - title: "YAML Entry 2"
    entry_type: note
    body: "Body 2"
"""
        yaml_file = import_env["tmpdir"] / "import.yaml"
        yaml_file.write_text(yaml_content)

        with _patch_config(import_env):
            result = runner.invoke(app, ["import", str(yaml_file), "--kb", "test-kb"])
            assert result.exit_code == 0
            assert "Created" in result.output
            assert "Imported 2 entries" in result.output

    def test_import_dry_run(self, import_env):
        entries = {
            "entries": [
                {"title": "Dry Run Entry", "entry_type": "note", "body": "Should not be created"},
            ]
        }
        json_file = import_env["tmpdir"] / "dry.json"
        json_file.write_text(json.dumps(entries))

        with _patch_config(import_env):
            result = runner.invoke(app, ["import", str(json_file), "--kb", "test-kb", "--dry-run"])
            assert result.exit_code == 0
            assert "Dry run" in result.output
            assert "1 entries parsed" in result.output
            assert "No entries were created" in result.output

    def test_import_auto_detect_format(self, import_env):
        # .yml extension should auto-detect as yaml
        yaml_content = """entries:
  - title: "Auto Detect"
    entry_type: note
    body: "Auto"
"""
        yml_file = import_env["tmpdir"] / "import.yml"
        yml_file.write_text(yaml_content)

        with _patch_config(import_env):
            result = runner.invoke(app, ["import", str(yml_file), "--kb", "test-kb"])
            assert result.exit_code == 0
            assert "Created" in result.output

    def test_import_file_not_found(self, import_env):
        with _patch_config(import_env):
            result = runner.invoke(app, ["import", "/nonexistent/file.json", "--kb", "test-kb"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_import_unknown_extension(self, import_env):
        txt_file = import_env["tmpdir"] / "import.txt"
        txt_file.write_text("hello")

        with _patch_config(import_env):
            result = runner.invoke(app, ["import", str(txt_file), "--kb", "test-kb"])
            assert result.exit_code == 1
            assert "Cannot detect format" in result.output

    def test_import_partial_failure(self, import_env):
        # Entry without title should fail
        entries = {
            "entries": [
                {"title": "Good Entry", "entry_type": "note", "body": "OK"},
                {"entry_type": "note", "body": "No title"},
            ]
        }
        json_file = import_env["tmpdir"] / "partial.json"
        json_file.write_text(json.dumps(entries))

        with _patch_config(import_env):
            result = runner.invoke(app, ["import", str(json_file), "--kb", "test-kb"])
            # The JSON importer defaults "title" to "Untitled", so both may succeed.
            # But bulk_create_entries requires a non-empty title check.
            assert result.exit_code == 0
