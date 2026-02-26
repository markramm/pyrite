"""
Plugin Context

Provides shared dependencies to plugins, replacing per-handler self-bootstrapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..config import PyriteConfig
    from ..schema import KBSchema
    from ..storage.database import PyriteDB


@dataclass
class PluginContext:
    """Shared context for plugin operations.

    Provides config, db, and request-scoped metadata to plugins,
    eliminating the need for each handler to call load_config()/PyriteDB().

    Supports dict-style access for backwards compatibility with hook context dicts.
    """

    config: PyriteConfig
    db: PyriteDB
    kb_name: str = ""
    user: str = ""
    operation: str = ""
    kb_schema: KBSchema | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for backwards compat with hooks expecting context['kb_name']."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style .get() for backwards compat."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key in self.extra

    def search_semantic(
        self, query: str, kb_name: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search using semantic (vector) search if available, falls back to FTS5.

        Args:
            query: Natural language search query
            kb_name: Filter to specific KB (None for all)
            limit: Maximum results to return

        Returns:
            List of matching entry dicts with id, kb_name, title, entry_type, snippet
        """
        kb = kb_name or self.kb_name

        # Try semantic search first
        try:
            from ..services.embedding_service import EmbeddingService, is_available

            if is_available() and self.db.vec_available:
                svc = EmbeddingService(self.db)
                results = svc.search(query, kb_name=kb, limit=limit)
                if results:
                    return results
        except Exception:
            pass

        # Fallback to FTS5 keyword search
        try:
            from ..services.search_service import SearchService

            search_svc = SearchService(self.db)
            return search_svc.search(query, kb_name=kb, limit=limit)
        except Exception:
            return []
