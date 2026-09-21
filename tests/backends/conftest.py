"""
Fixtures for backend conformance tests.

Parametrized so the same tests run against every SearchBackend implementation.
Add new backend IDs to the ``backend`` fixture params to test them.

The sqlite half gets a fresh temporary file per test. The postgres half has
only ``PYRITE_TEST_PG_URL`` -- one database for every test in the run -- and
each test calls ``create_all`` then ``drop_all`` on it. Serially that is fine.
Under ``pytest -n`` two workers are inside that sequence at once and one drops
the tables the other is selecting from, so tests fail with
``relation "entry" does not exist`` for reasons that have nothing to do with
the backend.

So each xdist worker gets its own *schema* on that one database and puts it
first on the connection's ``search_path``: ``create_all``/``drop_all`` then
touch only that worker's tables. Nothing about the backend needs this --
``PostgresBackend`` takes a session and an engine and never names a database --
and it needs no second container.
"""

import os
import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB

_BACKENDS = ["sqlite", "postgres"]


def _pg_url():
    """Return Postgres test URL or None if unavailable."""
    return os.environ.get("PYRITE_TEST_PG_URL")


def _worker_schema():
    """This xdist worker's schema name, or None when running serially.

    pytest-xdist sets PYTEST_XDIST_WORKER to ``gw0``, ``gw1``, ... in each
    worker process and leaves it unset under ``-n 0``, where one process owns
    the database and the public schema is safe to use.
    """
    return os.environ.get("PYTEST_XDIST_WORKER")


def _make_postgres_backend():
    """Create a PostgresBackend connected to the test database.

    Returns (backend, engine, session) — caller must drop tables on teardown.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from pyrite.storage.backends.postgres_backend import PostgresBackend, ensure_schema
    from pyrite.storage.models import Base

    url = _pg_url()
    worker = _worker_schema()

    if worker:
        with create_engine(url).connect() as conn:
            # The extension is per-database, not per-schema, and must be
            # somewhere every worker can see: pin it to public and keep public
            # on the search_path below, or the `vector` type fails to resolve
            # for every worker but whichever one created it first.
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector SCHEMA public"))
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{worker}"'))
            conn.commit()
        engine = create_engine(url, connect_args={"options": f"-csearch_path={worker},public"})
    else:
        engine = create_engine(url)

    # Create all ORM tables + Postgres-specific columns/triggers
    Base.metadata.create_all(engine)
    ensure_schema(engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    return PostgresBackend(session, engine), engine, session


def _teardown_postgres(engine, session):
    """Drop all tables to reset for next test."""
    from pyrite.storage.models import Base

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _require_pg():
    """Skip only when Postgres was never configured for this run."""
    if not _pg_url():
        pytest.skip("PYRITE_TEST_PG_URL not set")


def _setup_pg_backend(*kbs):
    """Build the postgres backend and register its KB rows.

    Deliberately not wrapped in ``except Exception: pytest.skip(...)``. That is
    how the shared-database race stayed invisible: a worker that lost it
    reported *skipped* with a message blaming an unavailable database, so the
    run stayed green while coverage silently evaporated -- 2 skips serially
    against 63 at ``-n 4``, and at the limit every postgres test skips and CI
    passes with the backend untested. An unreachable database is a skip
    (``_require_pg`` above); a database that is reachable but misbehaves is a
    failure, and must be loud.
    """
    be, engine, session = _make_postgres_backend()
    for name, kb_type, path, description in kbs:
        _register_pg_kb(session, name, kb_type, path, description)
    return be, engine, session


def _register_pg_kb(session, name, kb_type, path, description):
    """Register a KB row in Postgres (equivalent to PyriteDB.register_kb)."""
    from pyrite.storage.models import KB

    existing = session.query(KB).filter_by(name=name).first()
    if not existing:
        session.add(KB(name=name, kb_type=kb_type, path=path, description=description))
        session.commit()


@pytest.fixture(params=_BACKENDS)
def backend(request):
    """Yield a SearchBackend instance for each registered backend type."""
    if request.param == "sqlite":
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PyriteDB(Path(tmpdir) / "test.db")
            db.register_kb("test", "generic", "/tmp/test", "Test KB")
            yield db.backend
            db.close()
    elif request.param == "postgres":
        _require_pg()
        be, engine, session = _setup_pg_backend(("test", "generic", "/tmp/test", "Test KB"))
        try:
            yield be
        finally:
            _teardown_postgres(engine, session)
    else:
        pytest.skip(f"Unknown backend: {request.param}")


@pytest.fixture(params=_BACKENDS)
def backend_with_db(request):
    """Yield (backend, db) tuple — for tests that need KB registration etc."""
    if request.param == "sqlite":
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PyriteDB(Path(tmpdir) / "test.db")
            db.register_kb("test", "generic", "/tmp/test", "Test KB")
            db.register_kb("other", "generic", "/tmp/other", "Other KB")
            yield db.backend, db
            db.close()
    elif request.param == "postgres":
        _require_pg()
        be, engine, session = _setup_pg_backend(
            ("test", "generic", "/tmp/test", "Test KB"),
            ("other", "generic", "/tmp/other", "Other KB"),
        )
        try:
            yield be, None  # No PyriteDB for Postgres
        finally:
            _teardown_postgres(engine, session)
    else:
        pytest.skip(f"Unknown backend: {request.param}")
