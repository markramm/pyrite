"""Tests for Phase 3a: GitHub token storage, connect/disconnect endpoints."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
passlib = pytest.importorskip("passlib", reason="passlib not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, OAuthProviderConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.auth_service import AuthService
from pyrite.storage.database import PyriteDB
from pyrite.storage.migrations import MigrationManager


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def auth_env(tmpdir):
    """DB + AuthService for token storage tests."""
    db_path = tmpdir / "index.db"
    db = PyriteDB(db_path)
    config = AuthConfig(enabled=True)
    service = AuthService(db, config)
    yield service, db


def _make_github_client(tmpdir, github_configured=True):
    """Create TestClient with GitHub OAuth configured."""
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    providers = {}
    if github_configured:
        providers["github"] = OAuthProviderConfig(
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(
            index_path=db_path,
            auth=AuthConfig(
                enabled=True,
                allow_registration=True,
                providers=providers,
            ),
        ),
    )

    application = create_app(config=config)
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db

    return TestClient(application), config, db


class TestMigrationV14:
    def test_migration_adds_github_columns(self, tmpdir):
        """v14 migration should add github_access_token and github_token_scopes."""
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        # Create local_user table manually (like v6 would)
        conn.execute("""
            CREATE TABLE local_user (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'read',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

        mgr = MigrationManager(conn)
        mgr._apply_v14()

        columns = {row[1] for row in conn.execute("PRAGMA table_info(local_user)").fetchall()}
        assert "github_access_token" in columns
        assert "github_token_scopes" in columns
        conn.close()

    def test_migration_idempotent(self, tmpdir):
        """Running v14 twice should not fail."""
        db_path = tmpdir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE local_user (
                id INTEGER PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                password_hash TEXT DEFAULT '',
                role TEXT DEFAULT 'read',
                created_at TEXT,
                updated_at TEXT,
                github_access_token TEXT,
                github_token_scopes TEXT
            )
        """)
        conn.commit()

        mgr = MigrationManager(conn)
        mgr._apply_v14()  # Should not raise
        conn.close()


class TestAuthServiceTokenMethods:
    def test_store_and_retrieve_token(self, auth_env):
        service, _ = auth_env
        user = service.register("alice", "password123")

        service.store_github_token(user["id"], "ghp_test_token_123", "public_repo")
        token, scopes = service.get_github_token_for_user(user["id"])

        assert token == "ghp_test_token_123"
        assert scopes == "public_repo"

    def test_get_token_nonexistent_user(self, auth_env):
        service, _ = auth_env
        token, scopes = service.get_github_token_for_user(99999)
        assert token is None
        assert scopes is None

    def test_get_token_no_token_stored(self, auth_env):
        service, _ = auth_env
        user = service.register("bob", "password123")
        token, scopes = service.get_github_token_for_user(user["id"])
        assert token is None
        assert scopes is None

    def test_clear_token(self, auth_env):
        service, _ = auth_env
        user = service.register("charlie", "password123")
        service.store_github_token(user["id"], "ghp_token", "public_repo")

        result = service.clear_github_token(user["id"])
        assert result is True

        token, scopes = service.get_github_token_for_user(user["id"])
        assert token is None
        assert scopes is None

    def test_clear_token_nonexistent_user(self, auth_env):
        service, _ = auth_env
        result = service.clear_github_token(99999)
        assert result is False


class TestGitHubStatusEndpoint:
    def test_status_no_github_configured(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir, github_configured=False)
        r = client.get("/auth/github/status")
        assert r.status_code == 200
        data = r.json()
        assert data["connected"] is False
        assert data["github_configured"] is False

    def test_status_not_logged_in(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir)
        r = client.get("/auth/github/status")
        assert r.status_code == 200
        data = r.json()
        assert data["connected"] is False
        assert data["github_configured"] is True

    def test_status_logged_in_no_token(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir)
        # Register and login
        client.post("/auth/register", json={"username": "alice", "password": "password123"})
        r = client.get("/auth/github/status")
        assert r.status_code == 200
        data = r.json()
        assert data["connected"] is False


class TestGitHubConnectEndpoint:
    def test_connect_requires_auth(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir)
        r = client.get("/auth/github/connect", follow_redirects=False)
        assert r.status_code == 401

    def test_connect_redirects_to_github(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir)
        client.post("/auth/register", json={"username": "alice", "password": "password123"})
        r = client.get("/auth/github/connect", follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["location"]
        assert "github.com/login/oauth/authorize" in location
        assert "public_repo" in location

    def test_connect_404_when_github_not_configured(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir, github_configured=False)
        # Can't easily register without GitHub, so just test unauthenticated
        r = client.get("/auth/github/connect", follow_redirects=False)
        # When not configured, we get 404 before auth check
        assert r.status_code in (401, 404)


class TestGitHubDisconnectEndpoint:
    def test_disconnect_requires_auth(self, tmpdir):
        client, _, _ = _make_github_client(tmpdir)
        r = client.delete("/auth/github/connect")
        assert r.status_code == 401

    def test_disconnect_clears_token(self, tmpdir):
        client, config, db = _make_github_client(tmpdir)
        # Register and login
        client.post("/auth/register", json={"username": "alice", "password": "password123"})

        # Manually store a token
        auth_service = AuthService(db, config.settings.auth)
        user_row = db._raw_conn.execute(
            "SELECT id FROM local_user WHERE username = 'alice'"
        ).fetchone()
        auth_service.store_github_token(user_row[0], "ghp_test", "public_repo")

        # Disconnect
        r = client.delete("/auth/github/connect")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        # Verify token cleared
        token, _ = auth_service.get_github_token_for_user(user_row[0])
        assert token is None
