"""
Search backend abstraction layer.

Provides a protocol for pluggable search/index backends and the default
SQLiteBackend implementation.  LanceDBBackend is available when the
``lancedb`` package is installed.
"""

from .protocol import SearchBackend
from .sqlite_backend import SQLiteBackend

__all__ = ["SearchBackend", "SQLiteBackend"]

try:
    from .lancedb_backend import LanceDBBackend  # noqa: F401

    __all__.append("LanceDBBackend")
except ImportError:
    pass

try:
    from .postgres_backend import PostgresBackend  # noqa: F401

    __all__.append("PostgresBackend")
except ImportError:
    pass
