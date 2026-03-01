"""
Search backend abstraction layer.

Provides a protocol for pluggable search/index backends and the default
SQLiteBackend implementation.  PostgresBackend is available when the
``psycopg2`` and ``pgvector`` packages are installed.
"""

from .protocol import SearchBackend
from .sqlite_backend import SQLiteBackend

__all__ = ["SearchBackend", "SQLiteBackend"]

try:
    from .postgres_backend import PostgresBackend  # noqa: F401

    __all__.append("PostgresBackend")
except ImportError:
    pass
