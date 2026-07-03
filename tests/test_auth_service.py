"""Tests for AuthService: registration, login, sessions, roles."""

import tempfile
from pathlib import Path

import pytest

passlib = pytest.importorskip("passlib", reason="passlib not installed")

from pyrite.config import AuthConfig
from pyrite.services.auth_service import AuthService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def auth_env():
    """Create a fresh DB + AuthService for each test."""
    with tempfile.TemporaryDirectory() as d:
        db_path = Path(d) / "index.db"
        db = PyriteDB(db_path)
        config = AuthConfig(enabled=True)
        service = AuthService(db, config)
        yield service, db


class TestRegister:
    def test_first_user_is_admin(self, auth_env):
        service, _ = auth_env
        user = service.register("alice", "password123")
        assert user["role"] == "admin"
        assert user["username"] == "alice"

    def test_second_user_is_read(self, auth_env):
        service, _ = auth_env
        service.register("alice", "password123")
        user = service.register("bob", "password456")
        assert user["role"] == "read"

    def test_duplicate_username_raises(self, auth_env):
        service, _ = auth_env
        service.register("alice", "password123")
        with pytest.raises(ValueError, match="already taken"):
            service.register("alice", "password456")

    def test_empty_username_raises(self, auth_env):
        service, _ = auth_env
        with pytest.raises(ValueError, match="required"):
            service.register("", "password123")

    def test_short_password_raises(self, auth_env):
        service, _ = auth_env
        with pytest.raises(ValueError, match="at least 8"):
            service.register("alice", "short")

    def test_registration_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            db = PyriteDB(Path(d) / "index.db")
            config = AuthConfig(enabled=True, allow_registration=False)
            service = AuthService(db, config)
            with pytest.raises(ValueError, match="disabled"):
                service.register("alice", "password123")

    def test_display_name_stored(self, auth_env):
        service, _ = auth_env
        user = service.register("alice", "password123", display_name="Alice Smith")
        assert user["display_name"] == "Alice Smith"


class TestLogin:
    def test_login_success(self, auth_env):
        service, _ = auth_env
        service.register("alice", "password123")
        user, token = service.login("alice", "password123")
        assert user["username"] == "alice"
        assert len(token) > 20

    def test_login_wrong_password(self, auth_env):
        service, _ = auth_env
        service.register("alice", "password123")
        with pytest.raises(ValueError, match="Invalid"):
            service.login("alice", "wrongpass")

    def test_login_nonexistent_user(self, auth_env):
        service, _ = auth_env
        with pytest.raises(ValueError, match="Invalid"):
            service.login("nobody", "password123")


class TestSessions:
    def test_verify_session_valid(self, auth_env):
        service, _ = auth_env
        service.register("alice", "password123")
        _, token = service.login("alice", "password123")
        user = service.verify_session(token)
        assert user is not None
        assert user["username"] == "alice"

    def test_verify_session_invalid_token(self, auth_env):
        service, _ = auth_env
        assert service.verify_session("bogus-token") is None

    def test_logout_deletes_session(self, auth_env):
        service, _ = auth_env
        service.register("alice", "password123")
        _, token = service.login("alice", "password123")
        assert service.logout(token) is True
        assert service.verify_session(token) is None

    def test_logout_nonexistent_token(self, auth_env):
        service, _ = auth_env
        assert service.logout("bogus") is False

    def test_logout_all(self, auth_env):
        service, _ = auth_env
        reg = service.register("alice", "password123")
        service.login("alice", "password123")
        service.login("alice", "password123")
        count = service.logout_all(reg["id"])
        assert count == 2

    def test_max_sessions_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            db = PyriteDB(Path(d) / "index.db")
            config = AuthConfig(enabled=True, max_sessions_per_user=2)
            service = AuthService(db, config)
            service.register("alice", "password123")
            _, t1 = service.login("alice", "password123")
            _, t2 = service.login("alice", "password123")
            _, t3 = service.login("alice", "password123")
            # Oldest session (t1) should have been evicted
            assert service.verify_session(t1) is None
            assert service.verify_session(t2) is not None
            assert service.verify_session(t3) is not None


class TestRoles:
    def test_get_user(self, auth_env):
        service, _ = auth_env
        reg = service.register("alice", "password123")
        user = service.get_user(reg["id"])
        assert user["username"] == "alice"

    def test_get_user_not_found(self, auth_env):
        service, _ = auth_env
        assert service.get_user(999) is None

    def test_set_role(self, auth_env):
        service, _ = auth_env
        reg = service.register("alice", "password123")
        service.register("bob", "password456")
        assert service.set_role(reg["id"], "write") is True
        user = service.get_user(reg["id"])
        assert user["role"] == "write"

    def test_set_invalid_role(self, auth_env):
        service, _ = auth_env
        reg = service.register("alice", "password123")
        with pytest.raises(ValueError, match="Invalid role"):
            service.set_role(reg["id"], "superadmin")


class TestOAuthStateStore:
    """oauth-state-store-persistence: CSRF state moved from an in-memory
    dict to the DB (oauth_state table, migration v22) so a process restart
    or multi-replica deploy doesn't invalidate an in-flight OAuth login."""

    def test_create_and_verify_roundtrip(self, auth_env):
        service, _ = auth_env
        state = service.create_oauth_state(flow="login")
        assert isinstance(state, str) and len(state) > 20

        data = service.verify_oauth_state(state)
        assert data is not None
        assert data["flow"] == "login"
        assert data["user_id"] is None

    def test_verify_consumes_state(self, auth_env):
        """A state token is single-use: verifying it once succeeds, a
        second verify of the same token must fail (already consumed)."""
        service, _ = auth_env
        state = service.create_oauth_state(flow="login")
        assert service.verify_oauth_state(state) is not None
        assert service.verify_oauth_state(state) is None

    def test_verify_unknown_state_returns_none(self, auth_env):
        service, _ = auth_env
        assert service.verify_oauth_state("nonexistent-state-token") is None

    def test_verify_expired_state_returns_none(self, auth_env):
        service, _ = auth_env
        state = service.create_oauth_state(flow="login", ttl_seconds=-1)
        assert service.verify_oauth_state(state) is None

    def test_create_stores_user_id_for_connect_flow(self, auth_env):
        service, _ = auth_env
        state = service.create_oauth_state(flow="connect", user_id=42)
        data = service.verify_oauth_state(state)
        assert data["flow"] == "connect"
        assert data["user_id"] == 42

    def test_cleanup_expired_states_removes_only_expired(self, auth_env):
        service, db = auth_env
        fresh = service.create_oauth_state(flow="login")
        stale = service.create_oauth_state(flow="login", ttl_seconds=-1)

        removed = service.cleanup_expired_oauth_states()
        assert removed >= 1

        rows = db.execute_sql("SELECT state FROM oauth_state")
        remaining = {r["state"] for r in rows}
        assert fresh in remaining
        assert stale not in remaining

    def test_create_probabilistically_sweeps_expired_states(self, auth_env, monkeypatch):
        """create_oauth_state does opportunistic cleanup on a 1-in-10 draw
        (same pattern as verify_session's session cleanup), so expired rows
        don't accumulate forever without a dedicated background task."""
        service, db = auth_env
        stale = service.create_oauth_state(flow="login", ttl_seconds=-1)

        # Force the probabilistic branch to fire on the next call.
        monkeypatch.setattr(
            "pyrite.services.auth_service.secrets.randbelow", lambda _n: 0
        )
        service.create_oauth_state(flow="login")

        rows = db.execute_sql("SELECT state FROM oauth_state WHERE state = :s", {"s": stale})
        assert rows == [], "expired state should have been swept by the probabilistic cleanup"

    def test_state_persists_across_service_instances_same_db(self, auth_env):
        """The whole point of the DB-backed store: state created on one
        AuthService instance must be verifiable from a second, independent
        instance backed by the same DB — simulating a process restart or
        a second replica reading the same DB."""
        service_a, db = auth_env
        state = service_a.create_oauth_state(flow="login")

        from pyrite.config import AuthConfig
        from pyrite.services.auth_service import AuthService

        service_b = AuthService(db, AuthConfig(enabled=True))
        data = service_b.verify_oauth_state(state)
        assert data is not None
        assert data["flow"] == "login"
