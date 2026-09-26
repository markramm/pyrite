"""Login must not block the event loop while it waits on the DB (#440).

`AuthService.login`, `register` and the GitHub OAuth callback are `async def`
route handlers (`pyrite/server/auth_endpoints.py`) that call straight into
synchronous DB work. Nothing configures a busy timeout either, so pysqlite's
5 s default applies. When a login's write is blocked behind another
connection holding SQLite's write lock (a long index sync, another writer),
that blocking call runs *inline on the event loop thread* -- so it stalls
every other request the server is holding open, not only the login itself.

The probe: hold the write lock from a second, independent sqlite3 connection
(the pattern in `tests/test_kb_commit.py`'s
`test_commit_kb_recovers_the_session_when_recording_fails_under_lock`), then
fire a login concurrently with a plain `GET /auth/config` -- an `async def`
endpoint with no DB dependency at all. `TestClient` used as a context manager
runs one background event loop (an anyio "blocking portal") shared by every
request dispatched to it from any thread, exactly like one real server
process serving concurrent requests -- so if the login handler blocks that
thread, `/auth/config` can only finish after the lock is released, whatever
code path it takes.

**Why `with test_client:` matters.** A bare `client.get(...)` outside a
`with client:` block opens a *fresh* event-loop thread (a fresh portal) per
call, so two such calls never share a loop and this bug cannot be observed
that way (measured while writing this test: two bare calls never contended,
even with the lock held). Only inside the context-manager form do concurrent
requests share the one loop a real server would.

Deterministic by construction, not by wall clock: a SQLAlchemy
`before_cursor_execute` hook signals a `threading.Event` the instant the
login's own write statement is issued -- so the test knows the login request
has actually reached the database, not merely that some time has passed --
and the write lock is released only via an explicit second `threading.Event`
the test controls. The assertion is about *order of completion* (did
`/auth/config` finish before or after the lock was released), never a timed
threshold.
"""

import re
import sqlite3
import threading
import urllib.parse
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import event

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")

from fastapi.testclient import TestClient

from pyrite.config import AuthConfig, KBConfig, OAuthProviderConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db
from pyrite.services.oauth_providers import OAuthProfile, OAuthToken
from pyrite.storage.connection import SQLITE_BUSY_TIMEOUT_MS
from pyrite.storage.database import PyriteDB
from tests.auth_seed import seed_user

_BARRIER_TIMEOUT = 60.0
_LOCK_TIMEOUT = 60.0
# Matches the first *write* statement (not a preceding read) each handler
# issues against a table this ticket's writers touch: `session` for login's
# insert, `local_user` for register's and oauth_login's insert/update,
# `oauth_state` for the callback's one-time-use delete (verify_oauth_state,
# which runs before oauth_login). A read (e.g. oauth_login's SELECT by
# provider id) never blocks behind another connection's write lock in WAL
# mode, so matching only DML here means the signal fires when the request
# has reached a statement that can actually be stuck, not merely dispatched.
_WRITE_STATEMENT = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE)\b.*\b(session|local_user|oauth_state)\b",
    re.IGNORECASE | re.DOTALL,
)

# Well under SQLITE_BUSY_TIMEOUT_MS -- see the comment at its use below.
SHORT_WAIT_S = 0.5


def _make_client(
    tmpdir: Path, providers: dict | None = None
) -> tuple[TestClient, PyriteConfig, PyriteDB]:
    db_path = tmpdir / "index.db"
    kb_path = tmpdir / "kb"
    kb_path.mkdir(exist_ok=True)

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="generic")],
        settings=Settings(
            index_path=db_path,
            auth=AuthConfig(enabled=True, allow_registration=True, providers=providers or {}),
        ),
    )
    application = create_app(config=config)
    db = PyriteDB(db_path)
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db
    seed_user(db, "alice", "password123", role="admin")
    return TestClient(application), config, db


@pytest.fixture
def env(tmp_path):
    test_client, config, db = _make_client(tmp_path)
    try:
        yield test_client, config.settings.index_path, db
    finally:
        db.close()


@pytest.fixture
def oauth_env(tmp_path):
    providers = {
        "github": OAuthProviderConfig(client_id="test-client-id", client_secret="test-secret")
    }
    test_client, config, db = _make_client(tmp_path, providers=providers)
    try:
        yield test_client, config.settings.index_path, db
    finally:
        db.close()


class _WriteLockHolder:
    """Holds SQLite's write lock on a second, independent connection until
    told to release it -- an explicit signal, not a sleep."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._release = threading.Event()
        self._acquired = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        conn = sqlite3.connect(str(self._db_path), timeout=_LOCK_TIMEOUT)
        conn.execute("BEGIN IMMEDIATE")
        self._acquired.set()
        self._release.wait(timeout=_LOCK_TIMEOUT)
        conn.rollback()
        conn.close()

    def __enter__(self) -> "_WriteLockHolder":
        self._thread.start()
        assert self._acquired.wait(timeout=_BARRIER_TIMEOUT), "never took the write lock"
        return self

    def release(self) -> None:
        self._release.set()
        self._thread.join(timeout=_BARRIER_TIMEOUT)

    def __exit__(self, *exc) -> None:
        self.release()


def _assert_request_does_not_block_the_loop(test_client, db_path, db, fire_request) -> None:
    """Fire ``fire_request()`` (a blocking call, e.g. ``test_client.post(...)``)
    on its own thread while a second connection holds SQLite's write lock,
    and assert a concurrent, DB-free ``GET /auth/config`` still completes
    while the lock is held.

    Shared by every handler this ticket covers (login, register, the OAuth
    callback): each does its own DB write, so each gets its own test below,
    all funneling through this one assertion.
    """
    # Fires the instant the request's own write reaches the (locked) session
    # table, so we know it has genuinely arrived at the database rather than
    # merely having been dispatched.
    reached_db = threading.Event()

    def _signal(conn, cursor, statement, *args):
        if _WRITE_STATEMENT.search(statement):
            reached_db.set()

    event.listen(db.engine, "before_cursor_execute", _signal)

    config_done = threading.Event()
    config_result: dict = {}

    def _do_config_request() -> None:
        r = test_client.get("/auth/config")
        config_result["status_code"] = r.status_code
        config_done.set()

    try:
        with test_client, _WriteLockHolder(db_path) as lock:
            request_thread = threading.Thread(target=fire_request, daemon=True)
            request_thread.start()
            assert reached_db.wait(timeout=_BARRIER_TIMEOUT), (
                "the request never reached the database -- nothing to race"
            )

            config_thread = threading.Thread(target=_do_config_request, daemon=True)
            config_thread.start()

            # /auth/config touches no DB at all, so a free event loop answers
            # it fast. The window here must stay well under
            # SQLITE_BUSY_TIMEOUT_MS: pysqlite's own busy handling eventually
            # raises "database is locked" and unblocks the loop on its own,
            # so a window close to (or past) the busy timeout would let that
            # expiry pass for "not blocked" instead of ever observing the
            # loop while it is genuinely still stuck. A short window forces
            # the assertion to catch the loop *during* the block, not after
            # it resolves itself.
            assert SHORT_WAIT_S * 1000 < SQLITE_BUSY_TIMEOUT_MS / 4, (
                "the wait window is not short enough relative to the busy "
                "timeout for this assertion to mean anything"
            )
            finished_while_locked = config_done.wait(timeout=SHORT_WAIT_S)

            lock.release()
            request_thread.join(timeout=_BARRIER_TIMEOUT)
            config_thread.join(timeout=_BARRIER_TIMEOUT)
    finally:
        event.remove(db.engine, "before_cursor_execute", _signal)

    assert config_done.is_set(), "/auth/config never completed"
    assert finished_while_locked, (
        "/auth/config -- an async endpoint with no DB dependency -- did not "
        "complete until the write lock was released, which means the "
        "request ahead of it blocked the shared event loop thread instead "
        "of running its DB work off of it"
    )
    assert config_result["status_code"] == 200


class TestLoginDoesNotBlockTheEventLoop:
    def test_login_blocked_on_a_writer_does_not_stall_a_concurrent_request(self, env):
        """RED today: the login handler runs its DB work inline on the event
        loop, so a concurrent, DB-free request queued behind it on the same
        loop cannot complete until the writer releases the lock -- even
        though that request never touches the database."""
        test_client, db_path, db = env
        _assert_request_does_not_block_the_loop(
            test_client,
            db_path,
            db,
            lambda: test_client.post(
                "/auth/login", json={"username": "alice", "password": "password123"}
            ),
        )


class TestRegisterDoesNotBlockTheEventLoop:
    def test_register_blocked_on_a_writer_does_not_stall_a_concurrent_request(self, env):
        """Same property for `/auth/register`'s account-creation write plus
        its auto-login (#440)."""
        test_client, db_path, db = env
        _assert_request_does_not_block_the_loop(
            test_client,
            db_path,
            db,
            lambda: test_client.post(
                "/auth/register", json={"username": "bob", "password": "password123"}
            ),
        )


class TestOAuthCallbackDoesNotBlockTheEventLoop:
    def test_callback_blocked_on_a_writer_does_not_stall_a_concurrent_request(self, oauth_env):
        """Same property for the GitHub OAuth callback's `oauth_login` write
        (#440). The provider exchange itself is mocked -- as in
        ``tests/test_auth_endpoints.py::TestOAuthEndpoints.test_callback_success``
        -- so only the DB work is under test, matching what #440 scopes:
        the auth handlers' own DB calls, not the provider network calls
        (which are already ``await``ed HTTP, not blocking)."""
        test_client, db_path, db = oauth_env

        # A valid, bound state row -- the same path test_callback_success uses:
        # hit /auth/github to mint one, and read its binding cookie back.
        start = test_client.get("/auth/github", follow_redirects=False)
        state = urllib.parse.parse_qs(urllib.parse.urlparse(start.headers["location"]).query)[
            "state"
        ][0]
        test_client.cookies.set("pyrite_oauth_binding", start.cookies["pyrite_oauth_binding"])

        mock_token = OAuthToken(access_token="gho_test")
        mock_profile = OAuthProfile(
            provider="github", provider_id="99", username="octocat", orgs=[]
        )

        def _fire_callback() -> None:
            with (
                patch(
                    "pyrite.server.auth_endpoints.GitHubOAuthProvider.exchange_code",
                    new_callable=AsyncMock,
                    return_value=mock_token,
                ),
                patch(
                    "pyrite.server.auth_endpoints.GitHubOAuthProvider.get_user_profile",
                    new_callable=AsyncMock,
                    return_value=mock_profile,
                ),
            ):
                test_client.get(
                    f"/auth/github/callback?code=testcode&state={state}",
                    follow_redirects=False,
                )

        _assert_request_does_not_block_the_loop(test_client, db_path, db, _fire_callback)

    def test_oauth_login_specifically_does_not_stall_a_concurrent_request(self, oauth_env):
        """Isolates `oauth_login`'s own write from `verify_oauth_state`'s:
        the state lookup is stubbed out (no DB), so the only write this
        request makes is `oauth_login`'s -- pinning that call's own
        threadpool wrap rather than relying on `verify_oauth_state`'s, which
        runs first and would otherwise mask a regression here."""
        test_client, db_path, db = oauth_env

        mock_token = OAuthToken(access_token="gho_test")
        mock_profile = OAuthProfile(
            provider="github", provider_id="99", username="octocat", orgs=[]
        )

        def _fire_callback() -> None:
            with (
                patch(
                    "pyrite.server.auth_endpoints.AuthService.verify_oauth_state",
                    return_value={"flow": "login"},
                ),
                patch(
                    "pyrite.server.auth_endpoints.GitHubOAuthProvider.exchange_code",
                    new_callable=AsyncMock,
                    return_value=mock_token,
                ),
                patch(
                    "pyrite.server.auth_endpoints.GitHubOAuthProvider.get_user_profile",
                    new_callable=AsyncMock,
                    return_value=mock_profile,
                ),
            ):
                test_client.get(
                    "/auth/github/callback?code=testcode&state=stubbed",
                    follow_redirects=False,
                )

        _assert_request_does_not_block_the_loop(test_client, db_path, db, _fire_callback)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
