"""
Search backend abstraction layer.

Provides a protocol for pluggable search/index backends and the default
SQLiteBackend implementation.
"""

from .protocol import SearchBackend
from .sqlite_backend import SQLiteBackend

__all__ = ["SearchBackend", "SQLiteBackend"]
