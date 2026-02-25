"""
Tests for REST API tier enforcement: role-based access control with read/write/admin tiers.

Tests cover:
- api_keys config field with hashed keys and roles
- Key-to-role resolution (single key, multi-key, no auth)
- requires_tier dependency enforcement
- Tier hierarchy: admin > write > read
- Backwards compatibility with existing api_key setting
- Endpoint tier annotations on real endpoints
"""

import hashlib
import tempfile
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db, resolve_api_key_role
from pyrite.storage.database import PyriteDB


def _hash_key(key: str) -> str:
    """SHA-256 hash a key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _make_client(tmpdir, api_key="", api_keys=None):
    """Create a TestClient with tier enforcement config."""
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    settings_kwargs = dict(
        index_path=db_path,
        api_key=api_key,
    )
    if api_keys is not None:
        settings_kwargs["api_keys"] = api_keys

    config = PyriteConfig(
        knowledge_bases=[
            KBConfig(name="test-kb", path=kb_path, kb_type="generic"),
        ],
        settings=Settings(**settings_kwargs),
    )

    application = create_app(config=config)
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db

    return TestClient(application), config


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# =============================================================================
# resolve_api_key_role unit tests
# =============================================================================


class TestResolveAPIKeyRole:
    """Test the key → role resolution logic."""

    def test_no_auth_returns_admin(self, tmpdir):
        """When auth is disabled (no api_key, no api_keys), everyone gets admin."""
        _, config = _make_client(tmpdir, api_key="", api_keys=[])
        role = resolve_api_key_role("anything", config)
        assert role == "admin"

    def test_no_auth_empty_key_returns_admin(self, tmpdir):
        """When auth is disabled, even empty key gives admin."""
        _, config = _make_client(tmpdir, api_key="", api_keys=[])
        role = resolve_api_key_role("", config)
        assert role == "admin"

    def test_single_api_key_correct_returns_admin(self, tmpdir):
        """Legacy single api_key: correct key returns admin."""
        _, config = _make_client(tmpdir, api_key="secret123")
        role = resolve_api_key_role("secret123", config)
        assert role == "admin"

    def test_single_api_key_wrong_returns_none(self, tmpdir):
        """Legacy single api_key: wrong key returns None."""
        _, config = _make_client(tmpdir, api_key="secret123")
        role = resolve_api_key_role("wrong", config)
        assert role is None

    def test_single_api_key_missing_returns_none(self, tmpdir):
        """Legacy single api_key: missing key returns None."""
        _, config = _make_client(tmpdir, api_key="secret123")
        role = resolve_api_key_role(None, config)
        assert role is None

    def test_api_keys_list_read_role(self, tmpdir):
        """api_keys list: key with read role returns 'read'."""
        keys = [{"key_hash": _hash_key("read-key"), "role": "read", "label": "Reader"}]
        _, config = _make_client(tmpdir, api_keys=keys)
        role = resolve_api_key_role("read-key", config)
        assert role == "read"

    def test_api_keys_list_write_role(self, tmpdir):
        """api_keys list: key with write role returns 'write'."""
        keys = [{"key_hash": _hash_key("write-key"), "role": "write", "label": "Writer"}]
        _, config = _make_client(tmpdir, api_keys=keys)
        role = resolve_api_key_role("write-key", config)
        assert role == "write"

    def test_api_keys_list_admin_role(self, tmpdir):
        """api_keys list: key with admin role returns 'admin'."""
        keys = [{"key_hash": _hash_key("admin-key"), "role": "admin", "label": "Admin"}]
        _, config = _make_client(tmpdir, api_keys=keys)
        role = resolve_api_key_role("admin-key", config)
        assert role == "admin"

    def test_api_keys_list_wrong_key_returns_none(self, tmpdir):
        """api_keys list: unrecognized key returns None."""
        keys = [{"key_hash": _hash_key("admin-key"), "role": "admin", "label": "Admin"}]
        _, config = _make_client(tmpdir, api_keys=keys)
        role = resolve_api_key_role("unknown-key", config)
        assert role is None

    def test_api_keys_and_single_key_coexist(self, tmpdir):
        """When both api_key and api_keys are set, api_keys takes precedence."""
        keys = [{"key_hash": _hash_key("list-key"), "role": "read", "label": "Reader"}]
        _, config = _make_client(tmpdir, api_key="legacy-key", api_keys=keys)
        # The list key works
        assert resolve_api_key_role("list-key", config) == "read"
        # Legacy key also works as admin (backwards compat)
        assert resolve_api_key_role("legacy-key", config) == "admin"


# =============================================================================
# Tier hierarchy tests
# =============================================================================


class TestTierHierarchy:
    """Test that tier hierarchy (admin > write > read) is enforced correctly."""

    def test_read_key_can_access_read_endpoints(self, tmpdir):
        """Read-tier key can access read-only endpoints (GET /api/kbs)."""
        keys = [{"key_hash": _hash_key("read-key"), "role": "read", "label": "R"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.get("/api/kbs", headers={"X-API-Key": "read-key"})
        assert resp.status_code == 200

    def test_read_key_cannot_access_write_endpoints(self, tmpdir):
        """Read-tier key is denied write-tier endpoints (POST /api/entries)."""
        keys = [{"key_hash": _hash_key("read-key"), "role": "read", "label": "R"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.post(
            "/api/entries",
            json={"title": "test", "body": "test", "kb": "test-kb"},
            headers={"X-API-Key": "read-key"},
        )
        assert resp.status_code == 403

    def test_read_key_cannot_access_admin_endpoints(self, tmpdir):
        """Read-tier key is denied admin-tier endpoints (POST /api/index/sync)."""
        keys = [{"key_hash": _hash_key("read-key"), "role": "read", "label": "R"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.post("/api/index/sync", headers={"X-API-Key": "read-key"})
        assert resp.status_code == 403

    def test_write_key_can_access_read_endpoints(self, tmpdir):
        """Write-tier key can access read-only endpoints."""
        keys = [{"key_hash": _hash_key("write-key"), "role": "write", "label": "W"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.get("/api/kbs", headers={"X-API-Key": "write-key"})
        assert resp.status_code == 200

    def test_write_key_can_access_write_endpoints(self, tmpdir):
        """Write-tier key can create entries."""
        keys = [{"key_hash": _hash_key("write-key"), "role": "write", "label": "W"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.post(
            "/api/entries",
            json={"title": "test", "body": "hello", "kb": "test-kb"},
            headers={"X-API-Key": "write-key"},
        )
        # 200 or 201 — just not 403
        assert resp.status_code != 403

    def test_write_key_cannot_access_admin_endpoints(self, tmpdir):
        """Write-tier key is denied admin endpoints."""
        keys = [{"key_hash": _hash_key("write-key"), "role": "write", "label": "W"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.post("/api/index/sync", headers={"X-API-Key": "write-key"})
        assert resp.status_code == 403

    def test_admin_key_can_access_all_tiers(self, tmpdir):
        """Admin-tier key can access read, write, and admin endpoints."""
        keys = [{"key_hash": _hash_key("admin-key"), "role": "admin", "label": "A"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        headers = {"X-API-Key": "admin-key"}

        # Read
        resp = client.get("/api/kbs", headers=headers)
        assert resp.status_code == 200

        # Write (create entry)
        resp = client.post(
            "/api/entries",
            json={"title": "test", "body": "hello", "kb": "test-kb"},
            headers=headers,
        )
        assert resp.status_code != 403

        # Admin (index sync)
        resp = client.post("/api/index/sync", headers=headers)
        assert resp.status_code != 403


# =============================================================================
# Backwards compatibility
# =============================================================================


class TestBackwardsCompatibility:
    """Existing behavior must not break."""

    def test_no_auth_all_endpoints_accessible(self, tmpdir):
        """When api_key is empty and no api_keys, everything works (current behavior)."""
        client, _ = _make_client(tmpdir, api_key="")
        assert client.get("/api/kbs").status_code == 200
        assert client.get("/api/stats").status_code == 200
        assert client.post("/api/index/sync").status_code == 200

    def test_single_api_key_all_endpoints_with_key(self, tmpdir):
        """Legacy single api_key grants admin access to all endpoints."""
        client, _ = _make_client(tmpdir, api_key="my-key")
        headers = {"X-API-Key": "my-key"}
        assert client.get("/api/kbs", headers=headers).status_code == 200
        assert client.get("/api/stats", headers=headers).status_code == 200
        assert client.post("/api/index/sync", headers=headers).status_code == 200

    def test_single_api_key_no_key_rejected(self, tmpdir):
        """Legacy single api_key: missing key still returns 401."""
        client, _ = _make_client(tmpdir, api_key="my-key")
        assert client.get("/api/kbs").status_code == 401

    def test_health_always_accessible(self, tmpdir):
        """Health endpoint never requires auth, regardless of config."""
        keys = [{"key_hash": _hash_key("k"), "role": "read", "label": "R"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        assert client.get("/health").status_code == 200


# =============================================================================
# Error responses
# =============================================================================


class TestTierErrorResponses:
    """Test that tier enforcement returns clear error messages."""

    def test_403_includes_required_tier(self, tmpdir):
        """403 response should indicate which tier is required."""
        keys = [{"key_hash": _hash_key("read-key"), "role": "read", "label": "R"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.post("/api/index/sync", headers={"X-API-Key": "read-key"})
        assert resp.status_code == 403
        body = resp.json()
        assert "admin" in body["detail"].lower() or "tier" in body["detail"].lower()

    def test_401_still_returned_for_missing_key(self, tmpdir):
        """When auth is enabled and no key provided, still get 401 not 403."""
        keys = [{"key_hash": _hash_key("k"), "role": "admin", "label": "A"}]
        client, _ = _make_client(tmpdir, api_keys=keys)
        resp = client.get("/api/kbs")
        assert resp.status_code == 401


# =============================================================================
# Settings serialization
# =============================================================================


class TestAPIKeysConfig:
    """Test api_keys field on Settings."""

    def test_settings_default_api_keys_empty(self):
        """Default Settings has empty api_keys list."""
        s = Settings()
        assert s.api_keys == []

    def test_settings_with_api_keys(self):
        """Settings accepts api_keys list."""
        keys = [{"key_hash": "abc123", "role": "read", "label": "Test"}]
        s = Settings(api_keys=keys)
        assert len(s.api_keys) == 1
        assert s.api_keys[0]["role"] == "read"

    def test_config_round_trip_with_api_keys(self):
        """api_keys should survive config serialization round-trip."""
        keys = [
            {"key_hash": "hash1", "role": "read", "label": "Reader"},
            {"key_hash": "hash2", "role": "admin", "label": "Admin"},
        ]
        config = PyriteConfig(settings=Settings(api_keys=keys))
        data = config.to_dict()
        assert data["settings"]["api_keys"] == keys

        restored = PyriteConfig.from_dict(data)
        assert len(restored.settings.api_keys) == 2
        assert restored.settings.api_keys[0]["role"] == "read"
