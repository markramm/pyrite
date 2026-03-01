"""
pyrite Storage Layer

SQLAlchemy ORM for standard tables, raw SQL for FTS5/sqlite-vec virtual tables.
"""

from .database import PyriteDB
from .document_manager import DocumentManager
from .index import IndexManager
from .models import (
    KB,
    Base,
    Entry,
    EntryTag,
    EntryVersion,
    Link,
    Repo,
    Source,
    Tag,
    User,
    WorkspaceRepo,
)
from .repository import KBRepository

__all__ = [
    "Base",
    "DocumentManager",
    "PyriteDB",
    "Entry",
    "EntryTag",
    "EntryVersion",
    "IndexManager",
    "KB",
    "KBRepository",
    "Link",
    "Repo",
    "Source",
    "Tag",
    "User",
    "WorkspaceRepo",
]
