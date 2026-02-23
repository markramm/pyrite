"""
Service Layer for pyrite

Provides unified business logic extracted from API, CLI, and UI layers.
Eliminates duplication and ensures consistent behavior across interfaces.
"""

from .git_service import GitService
from .kb_service import KBService
from .query_expansion_service import QueryExpansionService
from .repo_service import RepoService
from .search_service import SearchMode, SearchService
from .user_service import UserService

__all__ = [
    "GitService",
    "KBService",
    "QueryExpansionService",
    "RepoService",
    "SearchMode",
    "SearchService",
    "UserService",
]
