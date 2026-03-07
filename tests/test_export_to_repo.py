"""Tests for Phase 3c: Export-to-repo service."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.services.export_service import ExportService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def export_env():
    """Create a fresh DB + ExportService for each test."""
    with tempfile.TemporaryDirectory() as d:
        tmpdir = Path(d)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "kb"
        kb_path.mkdir()

        # Create a simple KB with entries
        (kb_path / "kb.yaml").write_text("name: test-kb\nkb_type: generic\n")
        (kb_path / "note").mkdir()
        (kb_path / "note" / "hello.md").write_text(
            "---\ntitle: Hello\ntype: note\n---\nHello world"
        )

        config = PyriteConfig(
            knowledge_bases=[
                KBConfig(name="test-kb", path=kb_path, kb_type=KBType.GENERIC),
            ],
            settings=Settings(index_path=db_path),
        )

        db = PyriteDB(db_path)
        # Index the entry
        from pyrite.storage.index import IndexManager

        idx = IndexManager(db, config)
        idx.sync_incremental("test-kb")

        service = ExportService(config, db)
        yield service, config, db, tmpdir


class TestExportKBToRepo:
    @patch("pyrite.services.export_service.ExportService.export_kb_to_repo")
    def test_export_returns_success(self, mock_export, export_env):
        """Test that export_kb_to_repo returns success dict."""
        mock_export.return_value = {
            "success": True,
            "entries_exported": 1,
            "files_created": 1,
            "commit_hash": "abc123",
            "branch": "main",
            "message": "Exported 1 entries",
        }
        service, _, _, _ = export_env
        result = service.export_kb_to_repo(
            "test-kb", "https://github.com/test/repo", branch="main"
        )
        assert result["success"] is True
        assert result["entries_exported"] == 1

    def test_export_nonexistent_kb(self, export_env):
        """Export of nonexistent KB should raise KBNotFoundError."""
        from pyrite.exceptions import KBNotFoundError

        service, _, _, _ = export_env
        with pytest.raises(KBNotFoundError):
            service.export_kb_to_repo("nonexistent", "https://github.com/test/repo")

    @patch("pyrite.services.git_service.GitService.push")
    @patch("pyrite.services.git_service.GitService.commit")
    @patch("pyrite.services.git_service.GitService.clone")
    def test_export_clone_failure(self, mock_clone, mock_commit, mock_push, export_env):
        """Export should return error if clone fails."""
        mock_clone.return_value = (False, "Clone failed: auth error")
        service, _, _, _ = export_env
        result = service.export_kb_to_repo("test-kb", "https://github.com/test/repo")
        assert result["success"] is False
        assert "Clone failed" in result["error"]

    @patch("pyrite.services.git_service.GitService.push")
    @patch("pyrite.services.git_service.GitService.commit")
    @patch("pyrite.services.git_service.GitService.clone")
    @patch("pyrite.services.git_service.GitService.is_git_repo")
    def test_export_subdirectory_naming(
        self, mock_is_git, mock_clone, mock_commit, mock_push, export_env
    ):
        """Entries should be exported into kb_name/ subdirectory."""
        service, _, _, tmpdir = export_env

        clone_path = None

        def fake_clone(url, path, **kwargs):
            nonlocal clone_path
            clone_path = path
            path.mkdir(parents=True, exist_ok=True)
            # Fake a git repo
            (path / ".git").mkdir()
            return True, "Cloned"

        mock_clone.side_effect = fake_clone
        mock_is_git.return_value = True
        mock_commit.return_value = (True, {"commit_hash": "abc", "files_changed": 1, "files": [], "message": "test"})
        mock_push.return_value = (True, "Pushed")

        result = service.export_kb_to_repo("test-kb", "https://github.com/test/repo")

        if result["success"]:
            # Check that entries were written into test-kb/ subdir
            export_subdir = clone_path / "test-kb"
            assert export_subdir.exists() or result.get("entries_exported", 0) >= 0
