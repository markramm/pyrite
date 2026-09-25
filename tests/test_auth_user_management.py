"""Admin user management over /auth/users* through the real app (#330).

The three /auth/users* handlers decide on the caller's role, but the /auth
router is mounted without the credential dependency (it must stay public for
/auth/login, /auth/register and /auth/config), so the role has to be resolved
per route. These tests drive `create_app` with auth enabled and real session
cookies from /auth/register and /auth/login:

- a global admin session can list users, change a role and read a user's
  per-KB permissions (and round-trip a KB grant under /api);
- a non-admin (read- or write-tier) session gets 403 on every /auth/users* route;
- no credential at all gets 401;
- a read- or write-tier API key gets 403;
- with auth disabled and no keys configured, the caller is admin, as on
  every /api admin route.
"""

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.storage.database import PyriteDB
from tests.test_api_tiers import _hash_key

USER_ROUTES = (
    ("GET", "/auth/users", None),
    ("PUT", "/auth/users/{id}/role", {"role": "write"}),
    ("GET", "/auth/users/{id}/permissions", None),
)


def _app(tmp_path, *, auth_enabled=True, api_keys=None):
    db_path = tmp_path / "index.db"
    kb_path = tmp_path / "kb"
    kb_path.mkdir(exist_ok=True)
    settings_kwargs = {
        "index_path": db_path,
        "auth": AuthConfig(enabled=auth_enabled, allow_registration=True),
    }
    if api_keys is not None:
        settings_kwargs["api_keys"] = api_keys
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(**settings_kwargs),
    )
    application = create_app(config=config)
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db
    return application, db


def _call(client, method, path, body, user_id):
    return client.request(method, path.format(id=user_id), json=body)


@pytest.fixture
def two_sessions(tmp_path):
    """(admin_client, member_client, anon_client, admin_id, member_id)."""
    application, db = _app(tmp_path)
    admin = TestClient(application)
    member = TestClient(application)
    anon = TestClient(application)

    r = admin.post("/auth/register", json={"username": "admin-user", "password": "password123"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "admin"
    admin_id = r.json()["id"]

    r = member.post("/auth/register", json={"username": "member", "password": "password123"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] != "admin"
    member_id = r.json()["id"]

    # A fresh login too, so the session cookie is the /auth/login one.
    r = member.post("/auth/login", json={"username": "member", "password": "password123"})
    assert r.status_code == 200, r.text

    try:
        yield admin, member, anon, admin_id, member_id
    finally:
        db.close()


class TestAdminSession:
    def test_admin_lists_users(self, two_sessions):
        admin, _, _, _, _ = two_sessions
        r = admin.get("/auth/users")
        assert r.status_code == 200, r.text
        names = {u["username"] for u in r.json()["users"]}
        assert names == {"admin-user", "member"}

    def test_admin_sets_role_and_it_takes_effect(self, two_sessions):
        admin, member, _, _, member_id = two_sessions
        r = admin.put(f"/auth/users/{member_id}/role", json={"role": "write"})
        assert r.status_code == 200, r.text
        assert r.json() == {"updated": True, "user_id": member_id, "role": "write"}

        me = member.get("/auth/me")
        assert me.status_code == 200, me.text
        assert me.json()["role"] == "write"

    def test_admin_reads_user_permissions(self, two_sessions):
        admin, _, _, _, member_id = two_sessions
        r = admin.get(f"/auth/users/{member_id}/permissions")
        assert r.status_code == 200, r.text
        assert r.json() == {"user_id": member_id, "permissions": {}}

    def test_admin_round_trips_a_kb_grant(self, two_sessions):
        """Regression guard: /api/kbs/{kb}/permissions already sees the admin."""
        admin, _, _, _, member_id = two_sessions
        r = admin.post("/api/kbs/test-kb/permissions", json={"user_id": member_id, "role": "write"})
        assert r.status_code == 200, r.text

        r = admin.get("/api/kbs/test-kb/permissions")
        assert r.status_code == 200, r.text
        grants = {g["user_id"]: g["role"] for g in r.json()["permissions"]}
        assert grants.get(member_id) == "write"

        r = admin.get(f"/auth/users/{member_id}/permissions")
        assert r.status_code == 200, r.text
        assert r.json()["permissions"] == {"test-kb": "write"}


class TestRefusals:
    @pytest.mark.parametrize(("method", "path", "body"), USER_ROUTES)
    def test_non_admin_session_is_forbidden(self, two_sessions, method, path, body):
        _, member, _, admin_id, _ = two_sessions
        r = _call(member, method, path, body, admin_id)
        assert r.status_code == 403, r.text

    @pytest.mark.parametrize(("method", "path", "body"), USER_ROUTES)
    def test_write_tier_session_is_forbidden(self, two_sessions, method, path, body):
        """The bar is admin, not merely above read."""
        admin, member, _, admin_id, member_id = two_sessions
        r = admin.put(f"/auth/users/{member_id}/role", json={"role": "write"})
        assert r.status_code == 200, r.text
        assert member.get("/auth/me").json()["role"] == "write"
        r = _call(member, method, path, body, admin_id)
        assert r.status_code == 403, r.text

    def test_non_admin_cannot_promote_itself(self, two_sessions):
        _, member, _, _, member_id = two_sessions
        r = member.put(f"/auth/users/{member_id}/role", json={"role": "admin"})
        assert r.status_code == 403, r.text
        assert member.get("/auth/me").json()["role"] != "admin"

    @pytest.mark.parametrize(("method", "path", "body"), USER_ROUTES)
    def test_no_credential_is_unauthenticated(self, two_sessions, method, path, body):
        _, _, anon, admin_id, _ = two_sessions
        r = _call(anon, method, path, body, admin_id)
        assert r.status_code == 401, r.text

    def test_public_auth_routes_stay_public(self, two_sessions):
        """The fix is per route: /auth/config needs no credential."""
        _, _, anon, _, _ = two_sessions
        assert anon.get("/auth/config").status_code == 200


class TestApiKeys:
    @pytest.fixture
    def keyed(self, tmp_path):
        keys = [
            {"key_hash": _hash_key("read-key"), "role": "read", "label": "Reader"},
            {"key_hash": _hash_key("write-key"), "role": "write", "label": "Writer"},
            {"key_hash": _hash_key("admin-key"), "role": "admin", "label": "Admin"},
        ]
        application, db = _app(tmp_path, api_keys=keys)
        client = TestClient(application)
        r = client.post("/auth/register", json={"username": "someone", "password": "password123"})
        assert r.status_code == 200, r.text
        client.cookies.clear()
        try:
            yield client, r.json()["id"]
        finally:
            db.close()

    @pytest.mark.parametrize("key", ["read-key", "write-key"])
    @pytest.mark.parametrize(("method", "path", "body"), USER_ROUTES)
    def test_non_admin_key_is_forbidden(self, keyed, method, path, body, key):
        client, user_id = keyed
        r = client.request(method, path.format(id=user_id), json=body, headers={"X-API-Key": key})
        assert r.status_code == 403, r.text

    def test_admin_key_lists_users(self, keyed):
        client, _ = keyed
        r = client.get("/auth/users", headers={"X-API-Key": "admin-key"})
        assert r.status_code == 200, r.text


class TestAuthDisabled:
    def test_no_auth_no_keys_is_admin(self, tmp_path):
        """Same contract as every /api admin route: no auth configured -> admin."""
        application, db = _app(tmp_path, auth_enabled=False)
        try:
            r = TestClient(application).get("/auth/users")
            assert r.status_code == 200, r.text
            assert r.json() == {"users": []}
        finally:
            db.close()


class TestLastAdmin:
    """The last global admin cannot be demoted: nobody could promote anyone
    back, and there is no in-product recovery (#330 cold read)."""

    def test_sole_admin_cannot_demote_self_over_http(self, two_sessions):
        admin, _, _, admin_id, _ = two_sessions
        r = admin.put(f"/auth/users/{admin_id}/role", json={"role": "read"})
        assert r.status_code == 409, r.text
        assert r.json()["detail"]["code"] == "LAST_ADMIN"
        assert admin.get("/auth/me").json()["role"] == "admin"
        assert admin.get("/auth/users").status_code == 200

    def test_sole_admin_may_reassert_admin(self, two_sessions):
        admin, _, _, admin_id, _ = two_sessions
        r = admin.put(f"/auth/users/{admin_id}/role", json={"role": "admin"})
        assert r.status_code == 200, r.text

    def test_one_of_two_admins_can_demote_the_other(self, two_sessions):
        admin, member, _, admin_id, member_id = two_sessions
        assert admin.put(f"/auth/users/{member_id}/role", json={"role": "admin"}).status_code == 200
        r = member.put(f"/auth/users/{admin_id}/role", json={"role": "write"})
        assert r.status_code == 200, r.text
        assert admin.get("/auth/me").json()["role"] == "write"
        # member is now the only admin, and is held there.
        r = member.put(f"/auth/users/{member_id}/role", json={"role": "read"})
        assert r.status_code == 409, r.text
        assert member.get("/auth/me").json()["role"] == "admin"


class TestLastAdminService:
    """The rule lives in AuthService.set_role, not only in the route."""

    @pytest.fixture
    def auth(self, tmp_path):
        from pyrite.services.auth_service import AuthService

        db = PyriteDB(tmp_path / "index.db")
        try:
            yield AuthService(db, AuthConfig(enabled=True, allow_registration=True))
        finally:
            db.close()

    @pytest.mark.parametrize("role", ["read", "write"])
    def test_refused_and_unchanged(self, auth, role):
        from pyrite.exceptions import ValidationError

        first = auth.register("root", "password123")
        auth.register("other", "password123")
        assert first["role"] == "admin"
        with pytest.raises(ValidationError, match="last admin"):
            auth.set_role(first["id"], role)
        roles = {u["username"]: u["role"] for u in auth.list_users()}
        assert roles == {"root": "admin", "other": "read"}

    def test_allowed_when_another_admin_remains(self, auth):
        first = auth.register("root", "password123")
        other = auth.register("other", "password123")
        assert auth.set_role(other["id"], "admin") is True
        assert auth.set_role(first["id"], "read") is True
        roles = {u["username"]: u["role"] for u in auth.list_users()}
        assert roles == {"root": "read", "other": "admin"}

    def test_unknown_user_is_still_not_found(self, auth):
        auth.register("root", "password123")
        assert auth.set_role(9999, "read") is False

    def test_raises_last_admin_error_specifically(self, auth):
        """#416: the last-admin refusal is its own type, not the base
        ValidationError, so the route can label it 409 LAST_ADMIN without
        mislabeling every other validation failure the same way."""
        from pyrite.exceptions import LastAdminError

        first = auth.register("root", "password123")
        auth.register("other", "password123")
        with pytest.raises(LastAdminError):
            auth.set_role(first["id"], "read")


class TestLastAdminErrorType:
    """#416: LastAdminError is a distinct ValidationError subclass with its
    own error_code, so the route (and the central handler) can catch it by
    name instead of assuming every ValidationError from set_role is this
    one refusal."""

    def test_is_a_validation_error_with_its_own_code(self):
        from pyrite.exceptions import LastAdminError, ValidationError

        assert issubclass(LastAdminError, ValidationError)
        assert LastAdminError.error_code == "LAST_ADMIN"

    def test_other_validation_errors_from_set_role_are_422_not_409(self, two_sessions, monkeypatch):
        """A ValidationError from set_role that isn't the last-admin refusal
        must not be mislabeled 409 LAST_ADMIN by the route's except clause."""
        from pyrite.exceptions import ValidationError
        from pyrite.services.auth_service import AuthService

        def _boom(self, user_id, role):
            raise ValidationError("some other validation failure")

        monkeypatch.setattr(AuthService, "set_role", _boom)
        admin, _, _, admin_id, _ = two_sessions
        r = admin.put(f"/auth/users/{admin_id}/role", json={"role": "read"})
        assert r.status_code == 422, r.text
        assert r.json().get("code") == "VALIDATION_ERROR", r.text
