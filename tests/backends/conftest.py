"""
Fixtures for backend conformance tests.

Parametrized so the same tests run against every SearchBackend implementation.
Add new backend IDs to the ``backend`` fixture params to test them.
"""

import os
import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB

_BACKENDS = ["sqlite", "lancedb", "postgres"]


def _make_lancedb_backend(tmpdir):
    from pyrite.storage.backends.lancedb_backend import LanceDBBackend

    return LanceDBBackend(Path(tmpdir) / "lance_data")


def _pg_url():
    """Return Postgres test URL or None if unavailable."""
    return os.environ.get("PYRITE_TEST_PG_URL")


def _make_postgres_backend():
    """Create a PostgresBackend connected to the test database.

    Returns (backend, engine) — caller must drop tables on teardown.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from pyrite.storage.backends.postgres_backend import PostgresBackend, ensure_schema
    from pyrite.storage.models import Base

    url = _pg_url()
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
    elif request.param == "lancedb":
        with tempfile.TemporaryDirectory() as tmpdir:
            yield _make_lancedb_backend(tmpdir)
    elif request.param == "postgres":
        if not _pg_url():
            pytest.skip("PYRITE_TEST_PG_URL not set")
        try:
            be, engine, session = _make_postgres_backend()
            _register_pg_kb(session, "test", "generic", "/tmp/test", "Test KB")
            yield be
            _teardown_postgres(engine, session)
        except Exception as exc:
            pytest.skip(f"Postgres unavailable: {exc}")
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
    elif request.param == "lancedb":
        with tempfile.TemporaryDirectory() as tmpdir:
            be = _make_lancedb_backend(tmpdir)
            yield be, None  # No PyriteDB for LanceDB
    elif request.param == "postgres":
        if not _pg_url():
            pytest.skip("PYRITE_TEST_PG_URL not set")
        try:
            be, engine, session = _make_postgres_backend()
            _register_pg_kb(session, "test", "generic", "/tmp/test", "Test KB")
            _register_pg_kb(session, "other", "generic", "/tmp/other", "Other KB")
            yield be, None  # No PyriteDB for Postgres
            _teardown_postgres(engine, session)
        except Exception as exc:
            pytest.skip(f"Postgres unavailable: {exc}")
    else:
        pytest.skip(f"Unknown backend: {request.param}")
