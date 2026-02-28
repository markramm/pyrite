"""
Search Service

Unified search operations with FTS5 query sanitization and hybrid search.
Used by API, CLI, and UI layers.
"""

import re
from enum import StrEnum
from typing import Any

from ..storage.database import PyriteDB


class SearchMode(StrEnum):
    """Search mode for queries."""

    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class SearchService:
    """
    Service for search operations.

    Provides:
    - FTS5 query sanitization (handles hyphens, special chars)
    - Full-text search with filters
    - Timeline queries
    - Tag and actor analytics
    - AI-powered query expansion
    """

    def __init__(self, db: PyriteDB, settings: Any | None = None):
        self.db = db
        self._settings = settings
        self._expansion_service = None

    def _get_expansion_service(self):
        """Lazy-load QueryExpansionService from settings."""
        if self._expansion_service is not None:
            return self._expansion_service

        if self._settings is None:
            return None

        from .query_expansion_service import QueryExpansionService, is_available

        provider = getattr(self._settings, "ai_provider", "stub")
        if not is_available(provider):
            return None

        self._expansion_service = QueryExpansionService(
            provider=provider,
            model=getattr(self._settings, "ai_model", ""),
            api_key=getattr(self._settings, "ai_api_key", ""),
            api_base=getattr(self._settings, "ai_api_base", ""),
        )
        return self._expansion_service

    # =========================================================================
    # Query Sanitization
    # =========================================================================

    @staticmethod
    def sanitize_fts_query(query: str) -> str:
        """
        Sanitize a search query for FTS5.

        FTS5 interprets hyphens as NOT operators, which breaks searches for
        hyphenated terms like "alex-jones" or "2024-01-15".

        This method:
        - Quotes hyphenated words to treat them as literals
        - Preserves explicit FTS5 operators (AND, OR, NOT)
        - Preserves quoted phrases

        Examples:
            "alex-jones" -> '"alex-jones"'
            "alex jones" -> "alex jones" (unchanged)
            'alex AND "not-here"' -> 'alex AND "not-here"' (preserved)
        """
        # If query already contains FTS5 operators or quotes, assume user knows what they're doing
        if any(op in query.upper() for op in [" AND ", " OR ", " NOT ", '"']):
            return query

        # Quote hyphenated terms to prevent FTS5 interpreting hyphens as NOT
        sanitized = re.sub(r"(\S*-\S*)", r'"\1"', query)
        return sanitized

    # =========================================================================
    # Search Operations
    # =========================================================================

    def search(
        self,
        query: str,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sanitize: bool = True,
        mode: str | SearchMode = SearchMode.KEYWORD,
        expand: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search across entries.

        Args:
            query: Search query
            kb_name: Filter to specific KB (None for all)
            entry_type: Filter by type (event, actor, etc.)
            tags: Filter by tags (AND logic)
            date_from: Filter from date (YYYY-MM-DD)
            date_to: Filter to date (YYYY-MM-DD)
            limit: Max results
            offset: Pagination offset
            sanitize: Whether to sanitize query for FTS5 (default True)
            mode: Search mode - keyword, semantic, or hybrid
            expand: Whether to use AI query expansion for additional terms

        Returns:
            List of matching entries with snippets and rank
        """
        # Normalize mode
        if isinstance(mode, str):
            try:
                mode = SearchMode(mode)
            except ValueError:
                mode = SearchMode.KEYWORD

        # Normalize "All KBs" to None
        if kb_name == "All KBs":
            kb_name = None

        # Apply query expansion to the FTS5 query (keyword leg only)
        expanded_query = self._expand_query(query) if expand else query

        if mode == SearchMode.SEMANTIC:
            # Semantic uses original natural language query, not expanded
            return self._semantic_search(query, kb_name, limit, offset=offset)
        elif mode == SearchMode.HYBRID:
            return self._hybrid_search(
                query,
                kb_name,
                entry_type,
                tags,
                date_from,
                date_to,
                limit,
                offset,
                sanitize,
                expanded_query=expanded_query,
            )

        # Default: keyword search
        kw_query = expanded_query
        if sanitize:
            kw_query = self.sanitize_fts_query(kw_query)

        return self.db.search(
            query=kw_query,
            kb_name=kb_name,
            entry_type=entry_type,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    def _expand_query(self, query: str) -> str:
        """Expand query with AI-generated terms, returning OR-combined FTS5 query."""
        svc = self._get_expansion_service()
        if svc is None:
            return query

        terms = svc.expand(query)
        if not terms:
            return query

        # Combine: original query OR term1 OR term2 ...
        parts = [query] + terms
        return " OR ".join(parts)

    def _semantic_search(
        self,
        query: str,
        kb_name: str | None = None,
        limit: int = 50,
        max_distance: float = 1.3,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Pure semantic vector search."""
        from .embedding_service import EmbeddingService, is_available

        if not is_available() or not self.db.vec_available:
            return []

        svc = EmbeddingService(self.db)
        if not svc.has_embeddings():
            return []

        # sqlite-vec KNN doesn't support SQL OFFSET, so fetch limit+offset
        # and slice in Python
        results = svc.search_similar(
            query, kb_name=kb_name, limit=limit + offset, max_distance=max_distance
        )
        return results[offset:]

    def _hybrid_search(
        self,
        query: str,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
        sanitize: bool = True,
        expanded_query: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF).

        Combines FTS5 keyword results with vector similarity results.
        Falls back to keyword-only if no embeddings exist.
        """
        # Get keyword results — use expanded query for FTS5 leg if available
        fts_query = expanded_query if expanded_query else query
        kw_query = self.sanitize_fts_query(fts_query) if sanitize else fts_query
        keyword_results = self.db.search(
            query=kw_query,
            kb_name=kb_name,
            entry_type=entry_type,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            limit=limit * 2,
            offset=0,
        )

        # Try to get semantic results
        semantic_results = self._semantic_search(query, kb_name, limit=limit * 2)

        if not semantic_results:
            # No embeddings — fall back to keyword only
            return keyword_results[offset : offset + limit]

        # Reciprocal Rank Fusion
        k = 60  # RRF constant
        scores: dict[tuple[str, str], float] = {}
        entries: dict[tuple[str, str], dict[str, Any]] = {}

        for rank, result in enumerate(keyword_results):
            key = (result["id"], result["kb_name"])
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank)
            entries[key] = result

        for rank, result in enumerate(semantic_results):
            key = (result["id"], result["kb_name"])
            scores[key] = scores.get(key, 0) + 1.0 / (k + rank)
            if key not in entries:
                entries[key] = result

        # Sort by RRF score descending
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)

        results = []
        for key in sorted_keys[offset : offset + limit]:
            entry = entries[key]
            entry["rrf_score"] = scores[key]
            results.append(entry)

        return results

    def search_by_tag(
        self, tag: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by tag."""
        if kb_name == "All KBs":
            kb_name = None
        return self.db.search_by_tag(tag, kb_name, limit)

    # =========================================================================
    # Timeline
    # =========================================================================

    def get_timeline(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        min_importance: int = 1,
        kb_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get timeline events.

        Args:
            date_from: Filter from date
            date_to: Filter to date
            min_importance: Minimum importance level (1-10)
            kb_name: Filter to specific KB
            limit: Max results
        """
        if kb_name == "All KBs":
            kb_name = None

        results = self.db.get_timeline(
            date_from=date_from, date_to=date_to, min_importance=min_importance, kb_name=kb_name
        )

        return results[:limit]

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_tags(self, kb_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get tags with counts."""
        if kb_name == "All KBs":
            kb_name = None

        tags = self.db.get_all_tags(kb_name)
        return [{"name": name, "count": count} for name, count in tags[:limit]]

    def get_most_linked(self, kb_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get most referenced entries."""
        if kb_name == "All KBs":
            kb_name = None
        return self.db.get_most_linked(kb_name, limit)

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get entries with no links."""
        if kb_name == "All KBs":
            kb_name = None
        return self.db.get_orphans(kb_name)
