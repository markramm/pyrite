"""
Fixtures for backend conformance tests.

Parametrized so the same tests run against every SearchBackend implementation.
Add new backend IDs to the ``backend`` fixture params to test them.
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.storage.database import PyriteDB


@pytest.fixture(params=["sqlite"])
def backend(request):
    """Yield a SearchBackend instance for each registered backend type."""
    if request.param == "sqlite":
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PyriteDB(Path(tmpdir) / "test.db")
            db.register_kb("test", "generic", "/tmp/test", "Test KB")
            yield db.backend
            db.close()
    else:
        pytest.skip(f"Unknown backend: {request.param}")


@pytest.fixture(params=["sqlite"])
def backend_with_db(request):
    """Yield (backend, db) tuple — for tests that need KB registration etc."""
    if request.param == "sqlite":
        with tempfile.TemporaryDirectory() as tmpdir:
            db = PyriteDB(Path(tmpdir) / "test.db")
            db.register_kb("test", "generic", "/tmp/test", "Test KB")
            db.register_kb("other", "generic", "/tmp/other", "Other KB")
            yield db.backend, db
            db.close()
    else:
        pytest.skip(f"Unknown backend: {request.param}")
