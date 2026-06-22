"""
Unit tests for PostgresBackend._exec error handling.

Regression coverage for `postgres-backend-swallows-query-errors`: result
materialization failures must surface as StorageError, not be masked as an
empty list (which is indistinguishable from a legitimate zero-row result).

These use a mock session so they run without a live Postgres instance.
"""

from unittest.mock import MagicMock

import pytest

from pyrite.exceptions import StorageError
from pyrite.storage.backends.postgres_backend import PostgresBackend


def _backend_with_result(result):
    """Build a PostgresBackend whose session.execute() returns `result`."""
    session = MagicMock()
    session.execute.return_value = result
    return PostgresBackend(session, engine=None)


def test_exec_returns_rows_on_success():
    """Happy path: rows materialize into list of dicts."""
    result = MagicMock()
    result.fetchall.return_value = [(1, "a"), (2, "b")]
    result.keys.return_value = ["id", "name"]
    backend = _backend_with_result(result)

    rows = backend._exec("SELECT id, name FROM entry")

    assert rows == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]


def test_exec_returns_empty_list_on_zero_rows():
    """Legitimate zero-row result still returns [] — not an error."""
    result = MagicMock()
    result.fetchall.return_value = []
    result.keys.return_value = ["id", "name"]
    backend = _backend_with_result(result)

    assert backend._exec("SELECT id, name FROM entry WHERE 1=0") == []


def test_exec_raises_storage_error_on_materialization_failure():
    """A failure during result materialization must raise StorageError,
    not be silently swallowed into an empty list."""
    result = MagicMock()
    result.fetchall.side_effect = RuntimeError("driver decode error")
    backend = _backend_with_result(result)

    with pytest.raises(StorageError):
        backend._exec("SELECT id, name FROM entry")


def test_exec_chains_original_exception():
    """StorageError chains the underlying cause via `from e`."""
    boom = RuntimeError("strict zip mismatch")
    result = MagicMock()
    result.fetchall.side_effect = boom
    backend = _backend_with_result(result)

    with pytest.raises(StorageError) as exc_info:
        backend._exec("SELECT id, name FROM entry")

    assert exc_info.value.__cause__ is boom
