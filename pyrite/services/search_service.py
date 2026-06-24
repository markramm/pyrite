"""
Search Service

Unified search operations with FTS5 query sanitization and hybrid search.
Used by API, CLI, and UI layers.
"""

import logging
import re
import time
from enum import StrEnum
from typing import Any

from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


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

        FTS5 treats many punctuation characters as special syntax:
        - Hyphens as NOT operators
        - Dots as column filters (column.term)
        - Colons as column prefixes
        - @, #, /, !, ~, = as syntax errors

        This method:
        - Quotes tokens containing special characters to treat them as literals
        - Preserves explicit FTS5 operators (AND, OR, NOT)
        - Preserves already-quoted phrases

        Examples:
            "alex-jones" -> '"alex-jones"'
            "0.6 milestone" -> '"0.6" milestone'
            "alex jones" -> "alex jones" (unchanged)
            'alex AND "not-here"' -> 'alex AND "not-here"' (preserved)
        """
        # If query already contains FTS5 operators or quotes, assume user knows what they're doing
        if any(op in query.upper() for op in [" AND ", " OR ", " NOT ", '"']):
            return query

        # Quote any token containing FTS5-special characters
        # Matches tokens with at least one non-alphanumeric, non-space, non-underscore char
        sanitized = re.sub(r"(\S*[^\w\s]\S*)", r'"\1"', query)
        return sanitized

    @staticmethod
    def _relax_to_or(query: str) -> str | None:
        """OR-combine the terms of a bare multi-term query.

        FTS5 `MATCH` is implicit-AND, so a query like "orange county florida
        quarterly" requires *every* term — one absent word zeroes the result
        set. When an AND search finds nothing, retrying with the terms
        OR-combined ("orange OR county OR florida OR quarterly") recovers the
        near-misses.

        Returns the OR-combined query, or ``None`` when relaxation does not
        apply: a single term (nothing to relax), an empty query, or a query the
        user already wrote with explicit operators or quoted phrases (we honor
        their intent rather than widening it).
        """
        if not query or not query.strip():
            return None
        # Respect explicit operators / quoted phrases — same guard the
        # sanitizer uses to decide "the user knows what they want."
        if any(op in query.upper() for op in [" AND ", " OR ", " NOT ", '"']):
            return None
        terms = query.split()
        if len(terms) < 2:
            return None
        return " OR ".join(terms)

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
        include_archived: bool = False,
        fips: str | None = None,
        state: str | None = None,
        status: str | None = None,
        trace: dict[str, Any] | None = None,
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
            status: Filter to entries with this lifecycle status (e.g.
                "unprocessed"). Applies to keyword and hybrid modes; the
                semantic leg does not filter.

        Returns:
            List of matching entries with snippets and rank
        """
        # Observability trace — a caller may pass a dict to receive the
        # mode/fallback/latency decisions; we always keep a local one so the
        # structured log line below is emitted on every search. Held locally
        # (not on self) because the service instance is shared across requests
        # on the server/MCP side.
        tr: dict[str, Any] = trace if trace is not None else {}

        # Normalize mode
        if isinstance(mode, str):
            try:
                mode = SearchMode(mode)
            except ValueError:
                mode = SearchMode.KEYWORD

        # Normalize "All KBs" to None
        if kb_name == "All KBs":
            kb_name = None

        tr["requested_mode"] = mode.value
        tr["actual_mode"] = mode.value
        tr["reason"] = ""
        tr["relaxed"] = False
        tr["query_len"] = len(query)
        tr["kb"] = kb_name

        results: list[dict[str, Any]] = []
        start = time.perf_counter()
        try:
            # Apply query expansion to the FTS5 query (keyword leg only)
            expanded_query = self._expand_query(query) if expand else query

            if mode == SearchMode.SEMANTIC:
                # Semantic uses original natural language query, not expanded
                results = self._semantic_search(query, kb_name, limit, offset=offset)
                if not results:
                    # Semantic returned nothing (commonly: no embeddings).
                    tr["actual_mode"] = "keyword"
                    tr["reason"] = "semantic_empty_no_embeddings"
            elif mode == SearchMode.HYBRID:
                results = self._hybrid_search(
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
                    fips=fips,
                    state=state,
                    status=status,
                    trace=tr,
                )
            else:
                # Default: keyword search
                kw_query = expanded_query
                if sanitize:
                    kw_query = self.sanitize_fts_query(kw_query)

                def _run(q: str) -> list[dict[str, Any]]:
                    return self.db.search(
                        query=q,
                        kb_name=kb_name,
                        entry_type=entry_type,
                        tags=tags,
                        date_from=date_from,
                        date_to=date_to,
                        limit=limit,
                        offset=offset,
                        include_archived=include_archived,
                        fips=fips,
                        state=state,
                        status=status,
                    )

                results = _run(kw_query)

                # Implicit-AND zeroes out when one term is absent. On exactly 0
                # hits, retry once with the terms OR-combined so a near-miss
                # still surfaces. Skip when the user already used
                # operators/quotes — _relax_to_or returns None then.
                if not results:
                    relaxed = self._relax_to_or(expanded_query)
                    if relaxed:
                        logger.debug(
                            "keyword search 0 hits; retrying OR-relaxed: %r", relaxed
                        )
                        results = _run(relaxed)
                        tr["relaxed"] = True
                        if results:
                            tr["reason"] = "or_relaxation_recovered"
        finally:
            tr["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
            tr["result_count"] = len(results)

        logger.info(
            "search.query kb=%s mode=%s actual=%s reason=%s query_len=%d "
            "result_count=%d latency_ms=%s relaxed=%s",
            tr["kb"],
            tr["requested_mode"],
            tr["actual_mode"],
            tr["reason"] or "-",
            tr["query_len"],
            tr["result_count"],
            tr["latency_ms"],
            tr["relaxed"],
        )

        return results

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
        fips: str | None = None,
        state: str | None = None,
        status: str | None = None,
        trace: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF).

        Combines FTS5 keyword results with vector similarity results.
        Falls back to keyword-only if no embeddings exist.
        """
        # Get keyword results — use expanded query for FTS5 leg if available
        # Fetch enough candidates from each leg to cover offset + limit after fusion
        fetch_size = max(limit * 2, offset + limit)
        fts_query = expanded_query if expanded_query else query
        kw_query = self.sanitize_fts_query(fts_query) if sanitize else fts_query
        keyword_results = self.db.search(
            query=kw_query,
            kb_name=kb_name,
            entry_type=entry_type,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            limit=fetch_size,
            offset=0,
            fips=fips,
            state=state,
            status=status,
        )

        # Try to get semantic results
        semantic_results = self._semantic_search(query, kb_name, limit=fetch_size)

        # The semantic leg can't filter by status, so a wrong-status entry could
        # enter the fused set via the vector side. Drop those to keep the hybrid
        # result consistent with the keyword leg's status filter.
        if status:
            semantic_results = [
                r for r in semantic_results if r.get("status") == status
            ]

        if not semantic_results:
            # No embeddings — fall back to keyword only
            if trace is not None:
                trace["actual_mode"] = "keyword"
                trace["reason"] = "hybrid_no_embeddings"
            return keyword_results[offset : offset + limit]

        if trace is not None:
            trace["actual_mode"] = "hybrid"

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
