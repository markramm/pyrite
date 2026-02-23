"""Tests for RepoService — high-level repo operations."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.services.git_service import GitService
from pyrite.services.repo_service import RepoService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def db(temp_dir):
    db_path = temp_dir / "index.db"
    db = PyriteDB(db_path)
    yield db
    db.close()


@pytest.fixture
def config(temp_dir):
    workspace = temp_dir / "workspace"
    workspace.mkdir()
    return PyriteConfig(
        settings=Settings(
            index_path=temp_dir / "index.db",
            workspace_path=workspace,
        ),
    )


@pytest.fixture
def repo_service(config, db):
    return RepoService(config, db)


class TestRepoServiceListAndStatus:
    """Tests for list and status operations."""

    def test_list_repos_empty(self, repo_service):
        """list_repos returns empty when no repos."""
        repos = repo_service.list_repos()
        assert repos == []

    def test_list_repos_with_data(self, repo_service, db):
        """list_repos returns registered repos."""
        db.register_repo("org/kb1", "/tmp/a")
        db.register_repo("org/kb2", "/tmp/b")
        repos = repo_service.list_repos()
        assert len(repos) == 2

    def test_get_repo_status_not_found(self, repo_service):
        """get_repo_status returns error for nonexistent repo."""
        status = repo_service.get_repo_status("nonexistent")
        assert "error" in status

    def test_get_repo_status(self, repo_service, db, temp_dir):
        """get_repo_status returns detailed info."""
        repo_path = temp_dir / "test-repo"
        repo_path.mkdir()
        db.register_repo("org/kb", str(repo_path))
        db.register_kb("test-kb", KBType.RESEARCH, str(repo_path))
        # Link KB to repo
        repo = db.get_repo(name="org/kb")
        db._raw_conn.execute(
            "UPDATE kb SET repo_id = ? WHERE name = ?",
            (repo["id"], "test-kb"),
        )
        db._raw_conn.commit()

        with (
            patch.object(GitService, "get_current_branch", return_value="main"),
            patch.object(GitService, "get_head_commit", return_value="abc123"),
            patch.object(GitService, "is_git_repo", return_value=True),
        ):
            status = repo_service.get_repo_status("org/kb")

        assert status["name"] == "org/kb"
        assert status["kb_count"] == 1
        assert "test-kb" in status["kb_names"]


class TestDiscoverKBs:
    """Tests for KB discovery in repos."""

    def test_discover_kbs_with_kb_yaml(self, repo_service, temp_dir):
        """discover_kbs finds KBs by kb.yaml."""
        kb_path = temp_dir / "research"
        kb_path.mkdir()
        (kb_path / "kb.yaml").write_text(
            "name: my-research\nkb_type: research\ndescription: Test KB\n"
        )
        (kb_path / "actors").mkdir()

        kbs = repo_service.discover_kbs(temp_dir)
        assert len(kbs) >= 1
        assert any(kb.name == "my-research" for kb in kbs)

    def test_discover_kbs_empty(self, repo_service, temp_dir):
        """discover_kbs returns empty for dirs without kb.yaml."""
        kbs = repo_service.discover_kbs(temp_dir)
        assert kbs == []


class TestUnsubscribe:
    """Tests for unsubscribe."""

    def test_unsubscribe_not_found(self, repo_service):
        """unsubscribe returns error for nonexistent repo."""
        result = repo_service.unsubscribe("nonexistent")
        assert result["success"] is False

    def test_unsubscribe_removes_repo(self, repo_service, db, temp_dir, config):
        """unsubscribe removes repo and associated KBs."""
        # Register a repo with a KB
        repo = db.register_repo("org/kb", str(temp_dir / "test"))
        db.register_kb("test-kb", KBType.RESEARCH, str(temp_dir / "test"))
        db._raw_conn.execute("UPDATE kb SET repo_id = ? WHERE name = ?", (repo["id"], "test-kb"))
        db._raw_conn.commit()

        # Add KB to config too
        kb_config = KBConfig(
            name="test-kb",
            path=temp_dir / "test",
            kb_type=KBType.RESEARCH,
            repo="org/kb",
        )
        config.add_kb(kb_config)

        # Add workspace membership
        user = db.get_local_user()
        db.add_workspace_repo(user["id"], repo["id"])

        with patch("pyrite.services.repo_service.save_config"):
            result = repo_service.unsubscribe("org/kb")

        assert result["success"] is True
        assert "test-kb" in result["kbs_removed"]
        assert db.get_repo(name="org/kb") is None


class TestSubscribe:
    """Tests for subscribe (with git operations mocked)."""

    @patch("pyrite.services.repo_service.get_github_token", return_value=None)
    @patch("pyrite.services.repo_service.save_config")
    @patch.object(GitService, "clone")
    @patch.object(GitService, "get_head_commit", return_value="abc123")
    @patch.object(GitService, "is_git_repo", return_value=False)
    def test_subscribe_success(
        self,
        mock_is_git,
        mock_head,
        mock_clone,
        mock_save,
        mock_token,
        repo_service,
        config,
        temp_dir,
    ):
        """subscribe clones and registers repo."""
        workspace = config.settings.workspace_path

        def clone_side_effect(url, path, **kwargs):
            path.mkdir(parents=True, exist_ok=True)
            # Create a kb.yaml so discover works
            (path / "kb.yaml").write_text(
                "name: test-research\nkb_type: research\ndescription: Test\n"
            )
            return True, "Cloned"

        mock_clone.side_effect = clone_side_effect

        result = repo_service.subscribe("https://github.com/org/test-research")
        assert result["success"] is True
        assert result["repo"] == "org/test-research"
        assert len(result["kbs"]) >= 1

    def test_subscribe_invalid_url(self, repo_service):
        """subscribe fails for non-GitHub URLs."""
        result = repo_service.subscribe("https://gitlab.com/org/repo")
        assert result["success"] is False
        assert "parse" in result["error"].lower()


class TestSync:
    """Tests for sync."""

    def test_sync_no_repos(self, repo_service):
        """sync returns error when no repos exist."""
        result = repo_service.sync()
        assert result["success"] is False

    @patch("pyrite.services.repo_service.get_github_token", return_value=None)
    @patch.object(GitService, "pull", return_value=(True, "Already up to date"))
    @patch.object(GitService, "get_head_commit", return_value="abc123")
    def test_sync_up_to_date(
        self,
        mock_head,
        mock_pull,
        mock_token,
        repo_service,
        db,
        temp_dir,
    ):
        """sync reports up-to-date when no changes."""
        repo_path = temp_dir / "test-repo"
        repo_path.mkdir()
        db.register_repo("org/kb", str(repo_path))
        db.update_repo_synced("org/kb", "abc123")

        result = repo_service.sync("org/kb")
        assert result["success"] is True
        assert result["repos"]["org/kb"]["message"] == "Already up to date"
