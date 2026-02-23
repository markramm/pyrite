"""
SQLite Database with FTS5 for Multi-KB Search

Facade class composing focused mixin modules:
- connection.py — engine setup, extensions, migrations, plugin tables
- crud.py — entry insert/update/delete/get
- queries.py — search, graph, analytics, timeline
- kb_ops.py — KB registration and stats
- user_ops.py — user, repo, workspace, entry versions

All external code imports PyriteDB from this module. The public API is
unchanged; implementation is split across mixins for maintainability.
"""

from pathlib import Path

from .connection import ConnectionMixin
from .crud import CRUDMixin
from .kb_ops import KBOpsMixin
from .queries import QueryMixin
from .user_ops import UserOpsMixin


class PyriteDB(ConnectionMixin, KBOpsMixin, CRUDMixin, QueryMixin, UserOpsMixin):
    """
    SQLite database for indexing multiple knowledge bases.

    Uses SQLAlchemy ORM for standard tables and raw SQL for FTS5/sqlite-vec
    virtual tables. Provides full-text search, tag/actor analytics, link
    graph queries, and timeline operations.
    """

    def __init__(self, db_path: Path):
        self._init_connection(db_path)
