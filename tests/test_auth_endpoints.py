"""Tests for auth API endpoints: register, login, logout, session."""

import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
passlib = pytest.importorskip("passlib", reason="passlib not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.storage.database import PyriteDB


def _make_client(tmpdir, auth_enabled=True, allow_registration=True):
    """Create TestClient with auth-enabled config."""
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(
            index_path=db_path,
            auth=AuthConfig(
                enabled=auth_enabled,
                allow_registration=allow_registration,
            ),
        ),
    )

    application = create_app(config=config)
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db

    return TestClient(application), config, db


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def auth_client(tmpdir):
    """App with auth enabled."""
    client, config, db = _make_client(tmpdir)
    return client


@pytest.fixture
def noauth_client(tmpdir):
    """App with auth disabled (default behavior)."""
    client, config, db = _make_client(tmpdir, auth_enabled=False)
    return client


class TestAuthConfig:
    def test_config_endpoint_auth_enabled(self, auth_client):
        r = auth_client.get("/auth/config")
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is True
        assert data["allow_registration"] is True

    def test_config_endpoint_auth_disabled(self, noauth_client):
        r = noauth_client.get("/auth/config")
        assert r.status_code == 200
        assert r.json()["enabled"] is False


class TestRegisterEndpoint:
    def test_register_first_user(self, auth_client):
        r = auth_client.post("/auth/register", json={
            "username": "alice",
            "password": "password123",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "alice"
        assert data["role"] == "admin"

    def test_register_sets_cookie(self, auth_client):
        r = auth_client.post("/auth/register", json={
            "username": "alice",
            "password": "password123",
        })
        assert r.status_code == 200
        assert "pyrite_session" in r.cookies

    def test_register_duplicate(self, auth_client):
        auth_client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        r = auth_client.post("/auth/register", json={
            "username": "alice", "password": "password456",
        })
        assert r.status_code == 400

    def test_register_disabled(self, tmpdir):
        client, _, _ = _make_client(tmpdir, allow_registration=False)
        r = client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        assert r.status_code == 400


class TestLoginEndpoint:
    def test_login_success(self, auth_client):
        auth_client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        r = auth_client.post("/auth/login", json={
            "username": "alice", "password": "password123",
        })
        assert r.status_code == 200
        assert "pyrite_session" in r.cookies

    def test_login_wrong_password(self, auth_client):
        auth_client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        r = auth_client.post("/auth/login", json={
            "username": "alice", "password": "wrong",
        })
        assert r.status_code == 401


class TestMeEndpoint:
    def test_me_authenticated(self, auth_client):
        auth_client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        # Login to get the cookie
        auth_client.post("/auth/login", json={
            "username": "alice", "password": "password123",
        })
        r = auth_client.get("/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "alice"

    def test_me_unauthenticated(self, auth_client):
        r = auth_client.get("/auth/me")
        assert r.status_code == 401


class TestLogoutEndpoint:
    def test_logout_clears_session(self, auth_client):
        auth_client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        auth_client.post("/auth/login", json={
            "username": "alice", "password": "password123",
        })
        r = auth_client.post("/auth/logout")
        assert r.status_code == 200
        # After logout, /auth/me should fail
        r = auth_client.get("/auth/me")
        assert r.status_code == 401


class TestAPIWithAuth:
    def test_api_requires_auth_when_enabled(self, auth_client):
        """API endpoints return 401 when auth enabled and no session/key."""
        r = auth_client.get("/api/kbs")
        assert r.status_code == 401

    def test_api_works_with_session(self, auth_client):
        """API works when authenticated via session cookie."""
        auth_client.post("/auth/register", json={
            "username": "alice", "password": "password123",
        })
        auth_client.post("/auth/login", json={
            "username": "alice", "password": "password123",
        })
        r = auth_client.get("/api/kbs")
        assert r.status_code == 200

    def test_api_works_without_auth_when_disabled(self, noauth_client):
        """Default behavior preserved: no auth = admin access."""
        r = noauth_client.get("/api/kbs")
        assert r.status_code == 200
