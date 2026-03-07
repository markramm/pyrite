"""Tests for Phase 3b+3d: Repo REST endpoints."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
passlib = pytest.importorskip("passlib", reason="passlib not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, OAuthProviderConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db, get_repo_service
from pyrite.services.repo_service import RepoService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _make_client(tmpdir, mock_repo_service=None):
    """Create TestClient with auth enabled + optional repo service mock."""
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(
            index_path=db_path,
            auth=AuthConfig(enabled=True, allow_registration=True),
        ),
    )

    application = create_app(config=config)
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db

    if mock_repo_service:
        application.dependency_overrides[get_repo_service] = lambda: mock_repo_service

    client = TestClient(application)
    # Register and login to get write access
    client.post("/auth/register", json={"username": "testuser", "password": "password123"})

    return client, config, db


class TestListRepos:
    def test_list_repos_empty(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc.list_repos.return_value = []
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.get("/api/repos")
        assert r.status_code == 200
        data = r.json()
        assert data["repos"] == []

    def test_list_repos_returns_repos(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc.list_repos.return_value = [
            {
                "id": 1,
                "name": "owner/repo",
                "local_path": "/tmp/repo",
                "remote_url": "https://github.com/owner/repo",
                "owner": "owner",
                "visibility": "public",
                "default_branch": "main",
                "is_fork": 0,
            }
        ]
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.get("/api/repos")
        assert r.status_code == 200
        repos = r.json()["repos"]
        assert len(repos) == 1
        assert repos[0]["name"] == "owner/repo"


class TestSubscribe:
    def test_subscribe_success(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc.subscribe.return_value = {
            "success": True,
            "repo": "owner/repo",
            "path": "/tmp/repo",
            "kbs": ["my-kb"],
            "entries_indexed": 10,
        }
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/subscribe", json={"remote_url": "https://github.com/owner/repo"})
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert r.json()["kbs"] == ["my-kb"]

    def test_subscribe_failure(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc.subscribe.return_value = {"success": False, "error": "Path already exists"}
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/subscribe", json={"remote_url": "https://github.com/owner/repo"})
        assert r.status_code == 400


class TestFork:
    def test_fork_requires_github_token(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc._github_token = None
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/fork", json={"remote_url": "https://github.com/owner/repo"})
        assert r.status_code == 400
        assert "GITHUB_NOT_CONNECTED" in r.json()["detail"]["code"]

    def test_fork_success(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc._github_token = "ghp_test"
        mock_svc.fork_and_subscribe.return_value = {
            "success": True,
            "repo": "user/repo",
            "is_fork": True,
        }
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/fork", json={"remote_url": "https://github.com/owner/repo"})
        assert r.status_code == 200
        assert r.json()["is_fork"] is True


class TestSync:
    def test_sync_success(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc.sync.return_value = {
            "success": True,
            "repos": {"owner/repo": {"success": True, "changes": 3}},
        }
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/owner/repo/sync")
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestUnsubscribe:
    def test_unsubscribe_success(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc.unsubscribe.return_value = {
            "success": True,
            "repo": "owner/repo",
            "kbs_removed": ["my-kb"],
            "files_deleted": False,
        }
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.delete("/api/repos/owner/repo")
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestGitHubRepos:
    def test_github_repos_requires_token(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc._github_token = None
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.get("/api/github/repos")
        assert r.status_code == 400
        assert "GITHUB_NOT_CONNECTED" in r.json()["detail"]["code"]


class TestCreatePR:
    def test_pr_requires_github_token(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc._github_token = None
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/owner/repo/pr", json={"title": "Test PR"})
        assert r.status_code == 400
        assert "GITHUB_NOT_CONNECTED" in r.json()["detail"]["code"]

    def test_pr_success(self, tmpdir):
        mock_svc = MagicMock(spec=RepoService)
        mock_svc._github_token = "ghp_test"
        mock_svc.create_pr.return_value = {
            "success": True,
            "pr_url": "https://github.com/owner/repo/pull/1",
            "pr_number": 1,
        }
        client, _, _ = _make_client(tmpdir, mock_repo_service=mock_svc)

        r = client.post("/api/repos/owner/repo/pr", json={"title": "Test PR", "body": "Description"})
        assert r.status_code == 200
        assert r.json()["pr_url"] == "https://github.com/owner/repo/pull/1"
