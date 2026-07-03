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

    def test_undecryptable_token_fails_closed_not_returned_as_plaintext(self, auth_env, caplog):
        """fail-open-exception-sweep site #5, DECIDED 2026-07-03 (fail
        closed): when an encryption key IS configured but a stored value
        fails to decrypt (corrupted ciphertext, rotated/wrong key, or a
        legacy pre-encryption plaintext row now being read back after
        encryption was turned on), the raw undecryptable bytes must never
        be handed back as if they were a valid token -- that's silently
        authenticating with corrupt-key material. The caller must see
        "no usable token" (forcing reconnect), the same contract already
        used for no-token-stored, not the corrupted bytes."""
        import logging

        svc = auth_env["svc"]
        db = auth_env["db"]

        # Simulate a stored value that is not valid Fernet ciphertext --
        # covers both "corrupted" and "legacy plaintext" cases, since
        # Fernet.decrypt raises InvalidToken for anything that isn't
        # valid ciphertext for the current key, regardless of cause.
        db._raw_conn.execute(
            "UPDATE local_user SET github_access_token = 'not-valid-ciphertext' WHERE id = 1"
        )
        db._raw_conn.commit()

        with caplog.at_level(logging.WARNING, logger="pyrite.services.auth_service"):
            token, scopes = svc.get_github_token_for_user(1)

        assert token is None, (
            f"undecryptable stored value must not be returned as a token, got {token!r}"
        )
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, "expected a warning-level log when decryption fails"

    def test_undecryptable_api_key_fails_closed(self, auth_env, caplog):
        """Same contract for the API-key decryption path
        (get_user_api_key), which had the identical
        `except Exception: decrypted = raw_key` fallback."""
        import logging

        svc = auth_env["svc"]
        db = auth_env["db"]

        db._raw_conn.execute(
            "INSERT INTO user_api_key (user_id, provider, encrypted_key, model, "
            "created_at, updated_at) VALUES (1, 'anthropic', 'not-valid-ciphertext', "
            "'', '2026-01-01', '2026-01-01')"
        )
        db._raw_conn.commit()

        with caplog.at_level(logging.WARNING, logger="pyrite.services.auth_service"):
            result = svc.get_user_api_key(1, "anthropic")

        assert result is None, f"undecryptable stored API key must not be returned, got {result!r}"
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, "expected a warning-level log when API key decryption fails"
