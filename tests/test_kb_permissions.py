"""Tests for per-KB permissions: role resolution, grant/revoke, ephemeral KB creation."""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.services.auth_service import AuthService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def setup(tmpdir):
    """Create DB, config, and auth service with two users."""
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir()

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(
            index_path=db_path,
            auth=AuthConfig(
                enabled=True,
                anonymous_tier="read",
                ephemeral_min_tier="write",
                ephemeral_max_per_user=1,
            ),
        ),
    )
    db = PyriteDB(db_path)
    auth = AuthService(db, config.settings.auth)

    # Register admin (first user) and a regular user
    admin = auth.register("admin", "password123", "Admin User")
    user = auth.register("alice", "password123", "Alice")

    return auth, db, config, admin, user


class TestGetKBRole:
    def test_explicit_grant(self, setup):
        auth, db, config, admin, user = setup
        auth.grant_kb_permission(user["id"], "test-kb", "write", admin["id"])
        role = auth.get_kb_role(user["id"], "test-kb")
        assert role == "write"

    def test_kb_default_role(self, setup):
        auth, db, config, admin, user = setup
        # No explicit grant, KB default_role is "read"
        role = auth.get_kb_role(user["id"], "test-kb", kb_default_role="read")
        assert role == "read"

    def test_global_fallback(self, setup):
        auth, db, config, admin, user = setup
        # No grant, no KB default → falls back to user global role
        role = auth.get_kb_role(user["id"], "test-kb")
        assert role == "read"  # alice's global role

    def test_admin_override(self, setup):
        auth, db, config, admin, user = setup
        # Global admin always gets "admin" regardless of KB settings
        role = auth.get_kb_role(admin["id"], "test-kb", kb_default_role="none")
        assert role == "admin"

    def test_private_kb_no_grant(self, setup):
        auth, db, config, admin, user = setup
        # Private KB (default_role="none") without explicit grant → None
        role = auth.get_kb_role(user["id"], "private-kb", kb_default_role="none")
        assert role is None

    def test_private_kb_with_grant(self, setup):
        auth, db, config, admin, user = setup
        auth.grant_kb_permission(user["id"], "private-kb", "write", admin["id"])
        role = auth.get_kb_role(user["id"], "private-kb", kb_default_role="none")
        assert role == "write"

    def test_anonymous_user_public_kb(self, setup):
        auth, db, config, admin, user = setup
        role = auth.get_kb_role(None, "test-kb", kb_default_role="read")
        assert role == "read"

    def test_anonymous_user_private_kb(self, setup):
        auth, db, config, admin, user = setup
        role = auth.get_kb_role(None, "test-kb", kb_default_role="none")
        assert role is None

    def test_anonymous_user_no_default(self, setup):
        auth, db, config, admin, user = setup
        # No KB default → falls back to anonymous_tier from config
        role = auth.get_kb_role(None, "test-kb")
        assert role == "read"  # anonymous_tier in fixture


class TestGrantRevokePermissions:
    def test_grant_permission(self, setup):
        auth, db, config, admin, user = setup
        auth.grant_kb_permission(user["id"], "test-kb", "write", admin["id"])
        perms = auth.list_kb_permissions("test-kb")
        assert len(perms) == 1
        assert perms[0]["user_id"] == user["id"]
        assert perms[0]["role"] == "write"

    def test_grant_updates_existing(self, setup):
        auth, db, config, admin, user = setup
        auth.grant_kb_permission(user["id"], "test-kb", "read", admin["id"])
        auth.grant_kb_permission(user["id"], "test-kb", "write", admin["id"])
        perms = auth.list_kb_permissions("test-kb")
        assert len(perms) == 1
        assert perms[0]["role"] == "write"

    def test_revoke_permission(self, setup):
        auth, db, config, admin, user = setup
        auth.grant_kb_permission(user["id"], "test-kb", "write", admin["id"])
        ok = auth.revoke_kb_permission(user["id"], "test-kb")
        assert ok is True
        perms = auth.list_kb_permissions("test-kb")
        assert len(perms) == 0

    def test_revoke_nonexistent(self, setup):
        auth, db, config, admin, user = setup
        ok = auth.revoke_kb_permission(user["id"], "test-kb")
        assert ok is False

    def test_list_permissions_empty(self, setup):
        auth, db, config, admin, user = setup
        perms = auth.list_kb_permissions("nonexistent-kb")
        assert perms == []

    def test_invalid_role(self, setup):
        auth, db, config, admin, user = setup
        with pytest.raises(ValueError, match="Invalid role"):
            auth.grant_kb_permission(user["id"], "test-kb", "superadmin", admin["id"])

    def test_get_user_kb_permissions(self, setup):
        auth, db, config, admin, user = setup
        auth.grant_kb_permission(user["id"], "kb1", "read", admin["id"])
        auth.grant_kb_permission(user["id"], "kb2", "write", admin["id"])
        perms = auth.get_user_kb_permissions(user["id"])
        assert perms == {"kb1": "read", "kb2": "write"}


class TestEphemeralKBCreation:
    def test_create_ephemeral_kb(self, setup, tmpdir):
        auth, db, config, admin, user = setup
        # Give alice write role so she can create ephemeral KBs
        auth.set_role(user["id"], "write")

        from pyrite.services.ephemeral_service import EphemeralKBService

        eph_svc = EphemeralKBService(config, db)
        result = auth.create_user_ephemeral_kb(user["id"], eph_svc)
        assert result["ephemeral"] is True
        assert "name" in result

        # Verify admin grant was created
        perms = auth.list_kb_permissions(result["name"])
        assert len(perms) == 1
        assert perms[0]["user_id"] == user["id"]
        assert perms[0]["role"] == "admin"

    def test_ephemeral_kb_limit_exceeded(self, setup, tmpdir):
        auth, db, config, admin, user = setup
        auth.set_role(user["id"], "write")

        from pyrite.services.ephemeral_service import EphemeralKBService

        eph_svc = EphemeralKBService(config, db)

        # Create first (allowed)
        auth.create_user_ephemeral_kb(user["id"], eph_svc)

        # Second should fail (limit=1)
        with pytest.raises(ValueError, match="limit reached"):
            auth.create_user_ephemeral_kb(user["id"], eph_svc)

    def test_ephemeral_kb_insufficient_tier(self, setup, tmpdir):
        auth, db, config, admin, user = setup
        # alice has 'read' role, needs 'write' for ephemeral

        from pyrite.services.ephemeral_service import EphemeralKBService

        eph_svc = EphemeralKBService(config, db)

        with pytest.raises(ValueError, match="Insufficient tier"):
            auth.create_user_ephemeral_kb(user["id"], eph_svc)

    def test_admin_can_create_ephemeral(self, setup, tmpdir):
        auth, db, config, admin, user = setup

        from pyrite.services.ephemeral_service import EphemeralKBService

        eph_svc = EphemeralKBService(config, db)
        result = auth.create_user_ephemeral_kb(admin["id"], eph_svc)
        assert result["ephemeral"] is True
