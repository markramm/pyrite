"""Tests for GitHub token encryption at rest."""

import os
import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.auth_service import AuthService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def auth_env(monkeypatch):
    """Auth environment with encryption key set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "index.db"
        config = PyriteConfig(
            knowledge_bases=[],
            settings=Settings(index_path=db_path),
        )
        db = PyriteDB(db_path)

        # Set encryption key
        monkeypatch.setenv("PYRITE_ENCRYPTION_KEY", "test-secret-key-for-unit-tests")

        svc = AuthService(db, config.settings)

        # Create a test user
        conn = db._raw_conn
        conn.execute(
            "INSERT INTO local_user (id, username, password_hash, created_at, updated_at) "
            "VALUES (1, 'testuser', 'hash', '2026-01-01', '2026-01-01')"
        )
        conn.commit()

        yield {"svc": svc, "db": db, "config": config}
        db.close()


@pytest.fixture
def auth_env_no_key(monkeypatch):
    """Auth environment without encryption key (plaintext fallback)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "index.db"
        config = PyriteConfig(
            knowledge_bases=[],
            settings=Settings(index_path=db_path),
        )
        db = PyriteDB(db_path)

        # Ensure no encryption key
        monkeypatch.delenv("PYRITE_ENCRYPTION_KEY", raising=False)

        svc = AuthService(db, config.settings)

        conn = db._raw_conn
        conn.execute(
            "INSERT INTO local_user (id, username, password_hash, created_at, updated_at) "
            "VALUES (1, 'testuser', 'hash', '2026-01-01', '2026-01-01')"
        )
        conn.commit()

        yield {"svc": svc, "db": db}
        db.close()


class TestTokenEncryption:
    def test_stored_token_is_not_plaintext_when_key_set(self, auth_env):
        """When PYRITE_ENCRYPTION_KEY is set, the raw DB value should not be the plaintext token."""
        svc = auth_env["svc"]
        db = auth_env["db"]

        svc.store_github_token(1, "ghp_secrettoken123456", "repo,read:user")

        # Read raw value from DB
        row = db._raw_conn.execute(
            "SELECT github_access_token FROM local_user WHERE id = 1"
        ).fetchone()
        raw_value = row[0]

        # Raw value should NOT be the plaintext token
        assert raw_value != "ghp_secrettoken123456"
        assert raw_value is not None

    def test_get_token_returns_plaintext(self, auth_env):
        """get_github_token_for_user should decrypt and return the original token."""
        svc = auth_env["svc"]

        svc.store_github_token(1, "ghp_secrettoken123456", "repo,read:user")
        token, scopes = svc.get_github_token_for_user(1)

        assert token == "ghp_secrettoken123456"
        assert scopes == "repo,read:user"

    def test_clear_token_works(self, auth_env):
        svc = auth_env["svc"]

        svc.store_github_token(1, "ghp_secrettoken123456")
        svc.clear_github_token(1)

        token, scopes = svc.get_github_token_for_user(1)
        assert token is None

    def test_plaintext_fallback_when_no_key(self, auth_env_no_key):
        """Without encryption key, tokens should still work (plaintext)."""
        svc = auth_env_no_key["svc"]

        svc.store_github_token(1, "ghp_plaintext123")
        token, scopes = svc.get_github_token_for_user(1)

        assert token == "ghp_plaintext123"

    def test_roundtrip_with_special_chars(self, auth_env):
        """Tokens with special characters should survive encrypt/decrypt."""
        svc = auth_env["svc"]

        weird_token = "ghp_abc+/=123!@#$%"
        svc.store_github_token(1, weird_token)
        token, _ = svc.get_github_token_for_user(1)

        assert token == weird_token
