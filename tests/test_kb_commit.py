"""Tests for KB commit and push operations (#55).

Tests git commit/push across all three interfaces: service layer, MCP, REST API.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.git_service import GitService
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager


@pytest.fixture
def git_kb(tmp_path):
    """Create a git-backed KB with sample entries."""
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()

    # Init git repo
    subprocess.run(["git", "init"], cwd=str(kb_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(kb_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(kb_path),
        capture_output=True,
    )

    # Create initial commit
    (kb_path / "README.md").write_text("# Test KB\n")
    subprocess.run(["git", "add", "."], cwd=str(kb_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(kb_path),
        capture_output=True,
    )

    kb = KBConfig(name="test-kb", path=kb_path, kb_type="generic")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    svc = KBService(config, db)

    yield {"kb_path": kb_path, "kb": kb, "config": config, "db": db, "svc": svc}
    db.close()


@pytest.fixture
def non_git_kb(tmp_path):
    """Create a KB without git."""
    kb_path = tmp_path / "no-git-kb"
    kb_path.mkdir()

    kb = KBConfig(name="no-git", path=kb_path, kb_type="generic")
    config = PyriteConfig(
        knowledge_bases=[kb],
        settings=Settings(index_path=tmp_path / "index.db"),
    )
    db = PyriteDB(tmp_path / "index.db")
    svc = KBService(config, db)

    yield {"kb_path": kb_path, "kb": kb, "config": config, "db": db, "svc": svc}
    db.close()


# =============================================================================
# GitService tests
# =============================================================================


class TestGitServiceCommit:
    """Test GitService.commit static method."""

    def test_commit_all_changes(self, git_kb):
        kb_path = git_kb["kb_path"]
        # Create an uncommitted file
        (kb_path / "note-1.md").write_text("---\ntitle: Note 1\n---\n\nHello")

        success, result = GitService.commit(kb_path, "Add note 1")
        assert success
        assert "commit_hash" in result
        assert result["files_changed"] >= 1

    def test_commit_specific_paths(self, git_kb):
        kb_path = git_kb["kb_path"]
        (kb_path / "note-a.md").write_text("---\ntitle: A\n---\n\nA")
        (kb_path / "note-b.md").write_text("---\ntitle: B\n---\n\nB")

        success, result = GitService.commit(
            kb_path, "Add note A only", paths=["note-a.md"]
        )
        assert success
        assert result["files_changed"] >= 1

        # note-b should still be untracked
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(kb_path),
            capture_output=True,
            text=True,
        )
        assert "note-b.md" in status.stdout

    def test_commit_nothing_to_commit(self, git_kb):
        kb_path = git_kb["kb_path"]
        success, result = GitService.commit(kb_path, "Empty commit")
        assert not success
        assert "nothing" in result.get("error", "").lower() or "no changes" in result.get("error", "").lower()

    def test_commit_not_git_repo(self, non_git_kb):
        kb_path = non_git_kb["kb_path"]
        success, result = GitService.commit(kb_path, "Should fail")
        assert not success

    def test_commit_with_sign_off(self, git_kb):
        kb_path = git_kb["kb_path"]
        (kb_path / "signed.md").write_text("---\ntitle: Signed\n---\n\nSigned")
        success, result = GitService.commit(
            kb_path, "Signed commit", sign_off=True
        )
        assert success

        # Verify sign-off in commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=str(kb_path),
            capture_output=True,
            text=True,
        )
        assert "Signed-off-by:" in log.stdout


class TestGitServicePush:
    """Test GitService.push static method."""

    def test_push_no_remote(self, git_kb):
        kb_path = git_kb["kb_path"]
        success, msg = GitService.push(kb_path)
        assert not success
        # No remote configured, should fail

    def test_push_with_remote(self, git_kb, tmp_path):
        kb_path = git_kb["kb_path"]
        # Create a bare remote
        remote_path = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=str(kb_path),
            capture_output=True,
        )

        success, msg = GitService.push(kb_path)
        assert success


class TestGitServiceStatus:
    """Test GitService.get_status static method."""

    def test_status_clean(self, git_kb):
        kb_path = git_kb["kb_path"]
        status = GitService.get_status(kb_path)
        assert status["clean"]
        assert status["staged"] == []
        assert status["unstaged"] == []
        assert status["untracked"] == []

    def test_status_with_changes(self, git_kb):
        kb_path = git_kb["kb_path"]
        (kb_path / "new.md").write_text("new content")
        (kb_path / "README.md").write_text("# Modified\n")

        status = GitService.get_status(kb_path)
        assert not status["clean"]
        assert "new.md" in status["untracked"]
        assert any("README.md" in f for f in status["unstaged"])


# =============================================================================
# KBService tests
# =============================================================================


class TestKBServiceCommit:
    """Test KBService.commit_kb method."""

    def test_commit_kb(self, git_kb):
        svc = git_kb["svc"]
        kb_path = git_kb["kb_path"]
        (kb_path / "entry.md").write_text("---\ntitle: Entry\n---\n\nContent")

        result = svc.commit_kb("test-kb", message="Add entry")
        assert result["success"]
        assert result["commit_hash"]
        assert result["files_changed"] >= 1

    def test_commit_kb_not_found(self, git_kb):
        svc = git_kb["svc"]
        with pytest.raises(Exception):  # KBNotFoundError or similar
            svc.commit_kb("nonexistent-kb", message="Fail")

    def test_commit_kb_not_git_repo(self, non_git_kb):
        svc = non_git_kb["svc"]
        (non_git_kb["kb_path"] / "test.md").write_text("test")
        with pytest.raises(Exception):
            svc.commit_kb("no-git", message="Fail")

    def test_commit_kb_specific_paths(self, git_kb):
        svc = git_kb["svc"]
        kb_path = git_kb["kb_path"]
        (kb_path / "keep.md").write_text("keep")
        (kb_path / "skip.md").write_text("skip")

        result = svc.commit_kb("test-kb", message="Partial", paths=["keep.md"])
        assert result["success"]

        # skip.md should still be uncommitted
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(kb_path),
            capture_output=True,
            text=True,
        )
        assert "skip.md" in status.stdout

    def test_push_kb(self, git_kb, tmp_path):
        svc = git_kb["svc"]
        kb_path = git_kb["kb_path"]

        # Create a bare remote
        remote_path = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote_path)], capture_output=True)
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_path)],
            cwd=str(kb_path),
            capture_output=True,
        )

        result = svc.push_kb("test-kb")
        assert result["success"]

    def test_push_kb_no_remote(self, git_kb):
        svc = git_kb["svc"]
        result = svc.push_kb("test-kb")
        assert not result["success"]


# =============================================================================
# MCP tool tests
# =============================================================================


class TestMCPCommitTools:
    """Test kb_commit and kb_push MCP tools at admin tier."""

    def test_commit_tool_registered_at_admin(self, git_kb):
        from pyrite.server.mcp_server import PyriteMCPServer

        server = PyriteMCPServer(config=git_kb["config"], tier="admin")
        assert "kb_commit" in server.tools
        assert "kb_push" in server.tools
        server.close()

    def test_commit_tool_not_at_write(self, git_kb):
        from pyrite.server.mcp_server import PyriteMCPServer

        server = PyriteMCPServer(config=git_kb["config"], tier="write")
        assert "kb_commit" not in server.tools
        assert "kb_push" not in server.tools
        server.close()

    def test_commit_tool_not_at_read(self, git_kb):
        from pyrite.server.mcp_server import PyriteMCPServer

        server = PyriteMCPServer(config=git_kb["config"], tier="read")
        assert "kb_commit" not in server.tools
        assert "kb_push" not in server.tools
        server.close()

    def test_commit_tool_handler(self, git_kb):
        from pyrite.server.mcp_server import PyriteMCPServer

        kb_path = git_kb["kb_path"]
        (kb_path / "mcp-entry.md").write_text("---\ntitle: MCP\n---\n\nMCP entry")

        server = PyriteMCPServer(config=git_kb["config"], tier="admin")
        handler = server.tools["kb_commit"]["handler"]
        result = handler({"kb": "test-kb", "message": "MCP commit"})
        assert result.get("success") or result.get("commit_hash")
        server.close()


# =============================================================================
# REST API tests
# =============================================================================


class TestRESTCommitEndpoints:
    """Test REST API commit/push endpoints."""

    def _make_app(self, config, db):
        from pyrite.server.api import create_app
        import pyrite.server.api as api_module

        api_module._config = config
        api_module._db = db
        api_module._kb_service = None
        api_module._index_mgr = None

        return create_app(config)

    def test_commit_endpoint(self, git_kb):
        from starlette.testclient import TestClient

        kb_path = git_kb["kb_path"]
        (kb_path / "api-entry.md").write_text("---\ntitle: API\n---\n\nAPI entry")

        app = self._make_app(git_kb["config"], git_kb["db"])
        client = TestClient(app)
        resp = client.post(
            "/api/kbs/test-kb/commit",
            json={"message": "API commit"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]

    def test_commit_endpoint_kb_not_found(self, git_kb):
        from starlette.testclient import TestClient

        app = self._make_app(git_kb["config"], git_kb["db"])
        client = TestClient(app)
        resp = client.post(
            "/api/kbs/nonexistent/commit",
            json={"message": "Should 404"},
        )
        assert resp.status_code == 404

    def test_push_endpoint_no_remote(self, git_kb):
        from starlette.testclient import TestClient

        app = self._make_app(git_kb["config"], git_kb["db"])
        client = TestClient(app)
        resp = client.post("/api/kbs/test-kb/push")
        assert resp.status_code == 200
        data = resp.json()
        assert not data["success"]
