"""GitHub OAuth state is bound to the browser that started the flow.

Through the real app and the real callback route; only GitHub's token
exchange and profile fetch are stubbed. Each "browser" is its own TestClient
with its own cookie jar.

Properties pinned here:

- a callback completes only when it carries the browser-binding cookie that
  was set when *this* state was issued (login and connect flows);
- the connect flow additionally requires the session of the user who started
  it, and stores nothing otherwise;
- the binding cookie is HttpOnly, SameSite=Lax, scoped to the GitHub routes,
  and cleared by the callback whatever its outcome;
- the database holds no usable copy of the binding value.
"""

import urllib.parse
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, OAuthProviderConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.auth_service import AuthService
from pyrite.services.oauth_providers import OAuthProfile, OAuthToken
from pyrite.storage.database import PyriteDB

# The browser-binding cookie's name is part of the interface (a reverse proxy
# or a CSP may need to know it), so it is spelled out here, not imported.
OAUTH_BINDING_COOKIE = "pyrite_oauth_binding"

PROFILE = OAuthProfile(
    provider="github",
    provider_id="777",
    username="victim-gh",
    display_name="Victim",
    email="v@example.com",
    avatar_url=None,
    orgs=[],
)


@pytest.fixture
def world(tmp_path: Path):
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(
            index_path=tmp_path / "index.db",
            auth=AuthConfig(
                enabled=True,
                allow_registration=True,
                providers={"github": OAuthProviderConfig(client_id="cid", client_secret="csecret")},
            ),
        ),
    )
    app = create_app(config=config)
    db = PyriteDB(tmp_path / "index.db")
    app.dependency_overrides[get_config] = lambda: config
    app.dependency_overrides[get_db] = lambda: db

    def browser() -> TestClient:
        return TestClient(app)

    yield {"browser": browser, "db": db, "auth": AuthService(db, config.settings.auth)}
    db.close()


def _stub_github():
    return (
        patch(
            "pyrite.server.auth_endpoints.GitHubOAuthProvider.exchange_code",
            new_callable=AsyncMock,
            return_value=OAuthToken(access_token="gho_victim", scope="public_repo"),
        ),
        patch(
            "pyrite.server.auth_endpoints.GitHubOAuthProvider.get_user_profile",
            new_callable=AsyncMock,
            return_value=PROFILE,
        ),
    )


def _state_of(response) -> str:
    assert response.status_code == 302, response.text
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(response.headers["location"]).query)
    return qs["state"][0]


def _callback(client: TestClient, state: str):
    a, b = _stub_github()
    with a, b:
        return client.get(
            f"/auth/github/callback?code=code-from-github&state={state}",
            follow_redirects=False,
        )


def _login_local(client: TestClient, username: str) -> int:
    r = client.post("/auth/register", json={"username": username, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------


class TestLoginFlowBinding:
    def test_same_browser_completes_login(self, world):
        browser = world["browser"]()
        state = _state_of(browser.get("/auth/github", follow_redirects=False))
        r = _callback(browser, state)
        assert r.headers["location"] == "/"
        assert "pyrite_session" in r.cookies

    def test_state_issued_to_another_browser_sets_no_session(self, world):
        attacker = world["browser"]()
        victim = world["browser"]()
        state = _state_of(attacker.get("/auth/github", follow_redirects=False))
        r = _callback(victim, state)
        assert "error=oauth_failed" in r.headers["location"]
        assert "pyrite_session" not in r.cookies
        assert not any(h.startswith("pyrite_session=") for h in _set_cookie_headers(r))

    def test_state_from_another_browser_refused_even_when_victim_has_own_flow(self, world):
        """The victim's browser holds a binding cookie of its own (it started
        a flow too); a state issued to someone else still does not match it."""
        attacker = world["browser"]()
        victim = world["browser"]()
        attacker_state = _state_of(attacker.get("/auth/github", follow_redirects=False))
        victim.get("/auth/github", follow_redirects=False)
        assert victim.cookies.get(OAUTH_BINDING_COOKIE)

        r = _callback(victim, attacker_state)
        assert "error=oauth_failed" in r.headers["location"]
        assert "pyrite_session" not in r.cookies

    def test_refused_callback_does_not_burn_the_real_flow(self, world):
        """A mismatched callback must not consume the legitimate browser's
        state: the attacker's browser still completes its own login."""
        attacker = world["browser"]()
        victim = world["browser"]()
        state = _state_of(attacker.get("/auth/github", follow_redirects=False))
        _callback(victim, state)
        r = _callback(attacker, state)
        assert r.headers["location"] == "/"

    def test_state_is_single_use_in_the_same_browser(self, world):
        browser = world["browser"]()
        r0 = browser.get("/auth/github", follow_redirects=False)
        state = _state_of(r0)
        binding = browser.cookies.get(OAUTH_BINDING_COOKIE)
        assert _callback(browser, state).headers["location"] == "/"
        # Replay with the same binding value restored.
        browser.cookies.set(OAUTH_BINDING_COOKIE, binding, path="/auth/github")
        browser.cookies.delete("pyrite_session")
        r = _callback(browser, state)
        assert "error=oauth_failed" in r.headers["location"]


# ---------------------------------------------------------------------------
# Connect flow
# ---------------------------------------------------------------------------


class TestConnectFlowBinding:
    def test_owner_completes_connect(self, world):
        owner = world["browser"]()
        owner_id = _login_local(owner, "owner")
        state = _state_of(owner.get("/auth/github/connect", follow_redirects=False))
        r = _callback(owner, state)
        assert r.headers["location"] == "/settings/kbs?github=connected"
        token, _ = world["auth"].get_github_token_for_user(owner_id)
        assert token == "gho_victim"

    def test_connect_completed_by_another_browser_stores_nothing(self, world):
        attacker = world["browser"]()
        attacker_id = _login_local(attacker, "attacker")
        victim = world["browser"]()
        _login_local(victim, "victim")
        state = _state_of(attacker.get("/auth/github/connect", follow_redirects=False))

        r = _callback(victim, state)
        assert "error=" in r.headers["location"]
        assert world["auth"].get_github_token_for_user(attacker_id)[0] is None

    def test_connect_with_binding_but_another_users_session_stores_nothing(self, world):
        """Even with the binding cookie (same physical browser), the connect
        callback completes only for the session user who started it."""
        attacker = world["browser"]()
        attacker_id = _login_local(attacker, "attacker")
        state = _state_of(attacker.get("/auth/github/connect", follow_redirects=False))
        binding = attacker.cookies.get(OAUTH_BINDING_COOKIE)

        other = world["browser"]()
        _login_local(other, "other")
        other.cookies.set(OAUTH_BINDING_COOKIE, binding, path="/auth/github")

        r = _callback(other, state)
        assert r.headers["location"] == "/settings/kbs?error=connect_failed"
        assert world["auth"].get_github_token_for_user(attacker_id)[0] is None

    def test_connect_with_binding_but_no_session_stores_nothing(self, world):
        attacker = world["browser"]()
        attacker_id = _login_local(attacker, "attacker")
        state = _state_of(attacker.get("/auth/github/connect", follow_redirects=False))
        attacker.cookies.delete("pyrite_session")

        r = _callback(attacker, state)
        assert r.headers["location"] == "/settings/kbs?error=connect_failed"
        assert world["auth"].get_github_token_for_user(attacker_id)[0] is None


# ---------------------------------------------------------------------------
# The binding cookie itself
# ---------------------------------------------------------------------------


class TestBindingCookie:
    @pytest.mark.parametrize("path", ["/auth/github", "/auth/github/connect"])
    def test_cookie_attributes(self, world, path):
        browser = world["browser"]()
        if path.endswith("connect"):
            _login_local(browser, "someone")
        r = browser.get(path, follow_redirects=False)
        headers = [h for h in _set_cookie_headers(r) if h.startswith(f"{OAUTH_BINDING_COOKIE}=")]
        assert len(headers) == 1, _set_cookie_headers(r)
        h = headers[0].lower()
        assert "httponly" in h
        assert "samesite=lax" in h
        assert "path=/auth/github" in h
        assert "max-age=" in h

    @pytest.mark.parametrize("good", [True, False])
    def test_callback_clears_the_cookie(self, world, good):
        browser = world["browser"]()
        state = _state_of(browser.get("/auth/github", follow_redirects=False))
        r = _callback(browser, state if good else "not-a-state")
        cleared = [h for h in _set_cookie_headers(r) if h.startswith(f"{OAUTH_BINDING_COOKIE}=")]
        assert cleared, _set_cookie_headers(r)
        assert "max-age=0" in cleared[0].lower()
        assert browser.cookies.get(OAUTH_BINDING_COOKIE) is None

    def test_database_holds_no_copy_of_state_or_binding(self, world):
        browser = world["browser"]()
        state = _state_of(browser.get("/auth/github", follow_redirects=False))
        binding = browser.cookies.get(OAUTH_BINDING_COOKIE)
        rows = world["db"].execute_sql("SELECT * FROM oauth_state")
        assert rows
        dumped = repr(rows)
        assert binding not in dumped
        assert state not in dumped
