"""Tests for extension CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from pyrite.cli.extension_commands import extension_app

runner = CliRunner()

# Create test app wrapping the extension sub-app
test_app = typer.Typer()
test_app.add_typer(extension_app, name="extension")


@pytest.mark.cli
class TestExtensionInit:
    def test_init_creates_files(self):
        """Extension init creates all expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "test-ext"
            result = runner.invoke(test_app, ["extension", "init", "test-ext", "--path", str(out_path)])

            assert result.exit_code == 0, result.output
            assert (out_path / "pyproject.toml").exists()
            assert (out_path / "src" / "pyrite_test_ext" / "__init__.py").exists()
            assert (out_path / "src" / "pyrite_test_ext" / "plugin.py").exists()
            assert (out_path / "src" / "pyrite_test_ext" / "entry_types.py").exists()
            assert (out_path / "src" / "pyrite_test_ext" / "validators.py").exists()
            assert (out_path / "src" / "pyrite_test_ext" / "preset.py").exists()
            assert (out_path / "tests" / "test_test_ext.py").exists()

    def test_init_with_types(self):
        """Extension init with --types generates dataclass entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "typed-ext"
            result = runner.invoke(
                test_app,
                ["extension", "init", "typed-ext", "--path", str(out_path), "--types", "article,review"],
            )

            assert result.exit_code == 0, result.output
            entry_types = (out_path / "src" / "pyrite_typed_ext" / "entry_types.py").read_text()
            assert "ArticleEntry" in entry_types
            assert "ReviewEntry" in entry_types
            assert '"article"' in entry_types
            assert '"review"' in entry_types

    def test_init_json_output(self):
        """Extension init with --format json produces valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "json-ext"
            result = runner.invoke(
                test_app,
                ["extension", "init", "json-ext", "--path", str(out_path), "--format", "json"],
            )

            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["status"] == "created"
            assert data["name"] == "json-ext"
            assert "files" in data

    def test_init_idempotent(self):
        """Extension init errors if pyproject.toml already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "existing-ext"
            out_path.mkdir()
            (out_path / "pyproject.toml").write_text("[project]\nname = 'existing'\n")

            result = runner.invoke(test_app, ["extension", "init", "existing-ext", "--path", str(out_path)])

            assert result.exit_code == 1
            assert "already exists" in result.output

    def test_init_generated_plugin_importable(self):
        """Generated plugin class can be imported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "importable-ext"
            result = runner.invoke(test_app, ["extension", "init", "importable-ext", "--path", str(out_path)])
            assert result.exit_code == 0, result.output

            # Add src to path and try importing
            import importlib
            import sys as _sys
            src_path = str(out_path / "src")
            _sys.path.insert(0, src_path)
            try:
                mod = importlib.import_module("pyrite_importable_ext.plugin")
                plugin = mod.ImportableExtPlugin()
                assert plugin.name == "importable_ext"
                assert isinstance(plugin.get_entry_types(), dict)
            finally:
                _sys.path.remove(src_path)


@pytest.mark.cli
class TestExtensionInstall:
    def test_install_rejects_missing_pyproject(self):
        """Install rejects path without pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(test_app, ["extension", "install", tmpdir])

            assert result.exit_code == 1
            assert "No pyproject.toml" in result.output

    def test_install_calls_pip(self):
        """Install calls pip with correct arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            (tmpdir / "pyproject.toml").write_text('[project]\nname = "test-pkg"\n')

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""

            with patch("pyrite.cli.extension_commands.subprocess.run", return_value=mock_result) as mock_run:
                result = runner.invoke(test_app, ["extension", "install", str(tmpdir)])

                assert result.exit_code == 0, result.output
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert "pip" in call_args[1] or call_args[2] == "pip"
                assert "install" in call_args
                assert "-e" in call_args

    def test_uninstall_calls_pip(self):
        """Uninstall calls pip with correct arguments."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("pyrite.cli.extension_commands.subprocess.run", return_value=mock_result) as mock_run:
            result = runner.invoke(test_app, ["extension", "uninstall", "test-ext", "--force"])

            assert result.exit_code == 0, result.output
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "uninstall" in call_args
            assert "pyrite-test-ext" in call_args


@pytest.mark.cli
class TestExtensionList:
    def test_list_with_plugins(self):
        """List shows installed plugins."""
        mock_registry = MagicMock()
        mock_registry.list_plugins.return_value = ["software_kb", "zettelkasten"]
        mock_plugin = MagicMock()
        mock_plugin.get_entry_types.return_value = {"adr": object, "component": object}
        mock_plugin.get_mcp_tools.return_value = {"tool1": {}}
        mock_registry.get.return_value = mock_plugin

        with patch("pyrite.plugins.get_registry", return_value=mock_registry):
            result = runner.invoke(test_app, ["extension", "list", "--format", "json"])

            assert result.exit_code == 0, result.output
            data = json.loads(result.output)
            assert data["count"] == 2
            assert len(data["plugins"]) == 2
