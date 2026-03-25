"""Tests for ExportService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.exceptions import KBNotFoundError, PyriteError
from pyrite.services.export_service import ExportService


@pytest.fixture
def mock_config():
    config = MagicMock()
    return config


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def export_svc(mock_config, mock_db):
    return ExportService(mock_config, mock_db)


class TestExportKBToDirectory:
    def test_exports_entries_as_markdown(self, export_svc, mock_config, mock_db, tmp_path):
        kb_cfg = MagicMock()
        kb_cfg.kb_yaml_path = tmp_path / "kb.yaml"
        kb_cfg.kb_yaml_path.write_text("name: test")
        mock_config.get_kb.return_value = kb_cfg

        mock_db.list_entries.return_value = [
            {
                "id": "entry1",
                "entry_type": "note",
                "title": "Test Entry",
                "body": "Hello world",
                "tags": ["foo", "bar"],
            }
        ]

        target = tmp_path / "export"
        result = export_svc.export_kb_to_directory("test", target)

        assert result["entries_exported"] == 1
        assert result["files_created"] == 1

        exported_file = target / "note" / "entry1.md"
        assert exported_file.exists()
        content = exported_file.read_text()
        assert "title: Test Entry" in content
        assert "Hello world" in content

    def test_raises_on_unknown_kb(self, export_svc, mock_config, tmp_path):
        mock_config.get_kb.return_value = None
        with pytest.raises(KBNotFoundError):
            export_svc.export_kb_to_directory("nonexistent", tmp_path / "out")

    def test_yaml_special_chars_in_title_are_quoted(self, export_svc, mock_config, mock_db, tmp_path):
        """Titles with YAML-special characters must be properly quoted."""
        kb_cfg = MagicMock()
        kb_cfg.kb_yaml_path = tmp_path / "kb.yaml"
        kb_cfg.kb_yaml_path.write_text("name: test")
        mock_config.get_kb.return_value = kb_cfg

        mock_db.list_entries.return_value = [
            {
                "id": "tricky",
                "entry_type": "note",
                "title": 'Value with: colon and "quotes"',
                "body": "Body text",
                "tags": [],
            }
        ]

        target = tmp_path / "export"
        export_svc.export_kb_to_directory("test", target)

        content = (target / "note" / "tricky.md").read_text()
        # The frontmatter should be parseable YAML
        import yaml
        parts = content.split("---")
        fm = yaml.safe_load(parts[1])
        assert fm["title"] == 'Value with: colon and "quotes"'

    def test_title_with_newline_does_not_inject_fields(self, export_svc, mock_config, mock_db, tmp_path):
        """Newlines in title must not inject additional YAML fields."""
        kb_cfg = MagicMock()
        kb_cfg.kb_yaml_path = tmp_path / "kb.yaml"
        kb_cfg.kb_yaml_path.write_text("name: test")
        mock_config.get_kb.return_value = kb_cfg

        mock_db.list_entries.return_value = [
            {
                "id": "inject",
                "entry_type": "note",
                "title": "Normal\nevil_field: injected",
                "body": "Body",
                "tags": [],
            }
        ]

        target = tmp_path / "export"
        export_svc.export_kb_to_directory("test", target)

        content = (target / "note" / "inject.md").read_text()
        import yaml
        parts = content.split("---")
        fm = yaml.safe_load(parts[1])
        # The evil_field should NOT appear as a separate key
        assert "evil_field" not in fm
        assert "injected" in fm["title"]


class TestCommitKB:
    @patch("pyrite.services.git_service.GitService")
    def test_delegates_to_git_service(self, mock_git_svc, export_svc, mock_config):
        kb_cfg = MagicMock()
        kb_cfg.path = Path("/fake/kb")
        mock_config.get_kb.return_value = kb_cfg
        mock_git_svc.is_git_repo.return_value = True
        mock_git_svc.commit.return_value = (True, {"commit_hash": "abc123", "files_changed": 2})

        result = export_svc.commit_kb("test", "my commit")

        mock_git_svc.commit.assert_called_once_with(
            Path("/fake/kb"), "my commit", paths=None, sign_off=False
        )
        assert result["success"] is True
        assert result["commit_hash"] == "abc123"

    @patch("pyrite.services.git_service.GitService")
    def test_raises_on_unknown_kb(self, mock_git_svc, export_svc, mock_config):
        mock_config.get_kb.return_value = None
        with pytest.raises(KBNotFoundError):
            export_svc.commit_kb("nonexistent", "msg")

    @patch("pyrite.services.git_service.GitService")
    def test_raises_on_non_git_repo(self, mock_git_svc, export_svc, mock_config):
        kb_cfg = MagicMock()
        kb_cfg.path = Path("/fake/kb")
        mock_config.get_kb.return_value = kb_cfg
        mock_git_svc.is_git_repo.return_value = False

        with pytest.raises(PyriteError, match="not in a git repository"):
            export_svc.commit_kb("test", "msg")


class TestPushKB:
    @patch("pyrite.services.git_service.GitService")
    def test_delegates_to_git_service(self, mock_git_svc, export_svc, mock_config):
        kb_cfg = MagicMock()
        kb_cfg.path = Path("/fake/kb")
        mock_config.get_kb.return_value = kb_cfg
        mock_git_svc.is_git_repo.return_value = True
        mock_git_svc.push.return_value = (True, "pushed successfully")

        result = export_svc.push_kb("test")

        mock_git_svc.push.assert_called_once_with(Path("/fake/kb"), remote="origin", branch=None)
        assert result["success"] is True
        assert result["message"] == "pushed successfully"

    @patch("pyrite.services.git_service.GitService")
    def test_raises_on_unknown_kb(self, mock_git_svc, export_svc, mock_config):
        mock_config.get_kb.return_value = None
        with pytest.raises(KBNotFoundError):
            export_svc.push_kb("nonexistent")
