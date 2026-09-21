"""Closing the DBs a REST app opens must leave no live SQLite connection.

This is the regression guard for the defect a cold read found on the branch
that introduced the `make_client` fixture: `create_app()` eagerly seeds the KB
registry, which opens a SECOND `PyriteDB` on the same file and parks it on
`application.state.pyrite_db`. Nothing in `pyrite/` ever closes that one, and
some routes read it directly rather than through dependency injection, so
closing only the DB the caller constructed leaves an open WAL connection --
the exact leak the fixture was written to eliminate
(`tests-leak-open-pyritedb-connections-into-temporarydirectory-teardown`).

The leak was invisible on that branch because the fixture also moved to
`tmp_path`, which pytest does not delete during the run. That is a real
mitigation but it is a *default* (`tmp_path_retention_policy`), not a
guarantee: flip the policy and every leaked connection is back to racing
`rmtree`. So this asserts on the connection, not on whether a directory
removal happened to survive.

**Why this test owns its own setup instead of using `make_client`.** The
thing under test is what happens *after* the connections are closed, and a
test that takes `make_client` cannot see that: the fixture closes them in its
teardown, which runs after the test body has finished. The file used to solve
that with two tests and a module-level dict -- the first stashed the
directory, the second asserted on it once teardown had run. That works only if
both land in the same process, and under `pytest -n` xdist is free to split
them, so the second failed with "the previous test did not run" for reasons
having nothing to do with the code under test (seen on PR #260's CI,
2026-09-21, while the same commit passed locally).

Building the app here instead makes the ordering internal to one test body:
open, close, assert, in that order, with no shared state and nothing for a
parallel runner to split. The setup mirrors `make_client` in the one respect
that matters -- `create_app(config=config)`, so the app's own connection lands
on the same file as ours. Without the config argument `create_app()` reads the
user's real configuration and opens `~/.pyrite/index.db`, the two connections
point at different files, and the leak has nowhere to show up.
"""

import pytest

from pyrite.config import PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

fastapi = pytest.importorskip("fastapi", reason="REST app tests need fastapi")


def _build_app(work_dir):
    """Build a REST app on `work_dir`, the way `make_client` does.

    Returns `(client, own_db, app_state_db)`. The caller owns both DBs.
    """
    from starlette.testclient import TestClient

    from pyrite.server.api import create_app, get_config, get_db

    kb_dir = work_dir / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "index.db"

    config = PyriteConfig(settings=Settings(index_path=db_path))
    application = create_app(config=config)

    own_db = PyriteDB(db_path)
    own_db.register_kb("test-kb", "generic", str(kb_dir), "Test KB")
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: own_db

    client = TestClient(application)
    return client, own_db, getattr(application.state, "pyrite_db", None)


def test_create_app_opens_a_second_connection(tmp_path):
    """Guard the premise: if this stops being true, the test below is vacuous."""
    client, own_db, app_state_db = _build_app(tmp_path / "premise")
    try:
        assert client.get("/api/kbs").status_code == 200
        assert app_state_db is not None, "create_app no longer parks a db on app.state"
        assert app_state_db is not own_db, (
            "create_app no longer opens its own second connection -- if this is "
            "now intentional, make_client's app-state tracking can be simplified"
        )
    finally:
        own_db.close()
        if app_state_db is not None and app_state_db is not own_db:
            app_state_db.close()


def test_no_wal_files_survive_closing_every_connection(tmp_path):
    """Close both connections, then assert the WAL and SHM files are gone.

    The close happens in this body rather than in fixture teardown, so the
    assertion can observe it. That is what lets this be one test.
    """
    work_dir = tmp_path / "closed"
    client, own_db, app_state_db = _build_app(work_dir)
    assert client.get("/api/kbs").status_code == 200

    own_db.close()
    if app_state_db is not None and app_state_db is not own_db:
        app_state_db.close()

    leftovers = sorted(p.name for p in work_dir.iterdir())
    live = [n for n in leftovers if n.endswith("-wal") or n.endswith("-shm")]
    assert not live, (
        f"SQLite WAL/SHM files are still live after every connection was "
        f"closed: {leftovers}. Some connection on this database was not closed "
        "-- most likely application.state.pyrite_db, which create_app opens and "
        "nothing in pyrite/ closes."
    )


def test_the_leak_is_visible_when_the_app_connection_is_left_open(tmp_path):
    """The guard above must be able to fail.

    A test that asserts "no WAL files" is worthless if the files would be
    absent anyway -- and they are absent, for instance, when `create_app()` is
    given no config and opens a different database entirely. Leaving the app's
    connection open is precisely the bug, so this pins that the assertion
    responds to it.
    """
    work_dir = tmp_path / "leaking"
    client, own_db, app_state_db = _build_app(work_dir)
    assert app_state_db is not None and app_state_db is not own_db

    own_db.close()  # the bug: app_state_db deliberately left open
    try:
        leftovers = sorted(p.name for p in work_dir.iterdir())
        live = [n for n in leftovers if n.endswith("-wal") or n.endswith("-shm")]
        assert live, (
            "leaving application.state.pyrite_db open produced no live WAL/SHM "
            f"files ({leftovers}), so the guard above cannot detect the leak it "
            "exists to catch -- most likely the two connections are no longer "
            "on the same database file"
        )
    finally:
        app_state_db.close()
