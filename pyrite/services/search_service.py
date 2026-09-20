"""
Search Service

Unified search operations with FTS5 query sanitization and hybrid search.
Used by API, CLI, and UI layers.
"""

import logging
import re
import sqlite3
import time
from enum import StrEnum
from typing import Any

from ..exceptions import QuerySyntaxError
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
    def _restrict(
        results: list[dict[str, Any]], kb_names: set[str] | list[str] | None, limit: int
    ) -> list[dict[str, Any]]:
        """Drop results from KBs the caller may not read (semantic/hybrid legs).

        The keyword leg filters in SQL; the vector KNN and the hybrid merge do
        not take an allowlist, so those legs over-fetch and are filtered here.
        """
        if kb_names is None:
            return results
        allowed = set(kb_names)
        return [r for r in results if r.get("kb_name") in allowed][:limit]

    def _db_search(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Call ``self.db.search`` and reclassify a raw FTS5 syntax error.

        ``sanitize_fts_query`` skips quoting when the query already contains
        an FTS5 operator (AND/OR/NOT) or a quote — it assumes the caller
        knows what they're doing. A bare special-char token like
        `cross-link` mixed into such a query then reaches SQLite's MATCH
        unquoted and raises ``sqlite3.OperationalError`` (e.g. "no such
        column: link"), because the hyphen/colon is parsed as column-filter
        syntax. That's a deterministic, non-retryable query problem, not an
        internal error — reclassify it before it escapes to CLI/MCP/REST.
        """
        try:
            return self.db.search(**kwargs)
        except sqlite3.OperationalError as e:
            raise QuerySyntaxError(
                f"Query could not be parsed: {e}. If your query uses AND/OR/NOT "
                "or phrase quotes, quote any tokens containing - : . yourself "
                "(sanitization is skipped once you use operators or quotes)."
            ) from e

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
        kb_names: set[str] | list[str] | None = None,
        warnings: list[str] | None = None,
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
            limit: Max results. A positive integer; anything else raises
                ``ValueError`` naming the value.
            offset: Pagination offset
            sanitize: Whether to sanitize query for FTS5 (default True)
            mode: Search mode - keyword, semantic, or hybrid
            expand: Whether to use AI query expansion for additional terms
            status: Filter to entries with this lifecycle status (e.g.
                "unprocessed").
            warnings: Optional list the caller passes in to receive
                human-readable notes about anything the search could not do
                as asked — today, a filter a backend's vector leg cannot
                honour, which costs the semantic leg entirely rather than
                returning rows that violate the filter. An empty list (or a
                list the search leaves untouched) means every filter was
                applied on every leg that ran. Never populated on the happy
                path; a caller that ignores it still gets correctly filtered
                results, just without knowing a leg was dropped.

        **What a search response owes its caller** (#56) — the one statement
        of the convention; the REST schema, the REST route and the ``kb_search``
        tool description point here rather than restating it:

        1. Every filter — ``entry_type``, ``tags``, ``date_from``/``date_to``,
           ``fips``, ``state``, ``status``, ``include_archived`` — is applied on
           **every** leg of every mode. Before #56 the vector leg ran unfiltered
           and the fused result silently contained entries the filter excluded.
        2. A leg that cannot honour a filter is dropped, never run unfiltered.
        3. A dropped leg is always named in ``warnings``. Silence means every
           filter was applied on every leg that ran, so an empty ``warnings``
           is *absent* on every surface — the MCP payload omits the key, REST
           omits it (``response_model_exclude_none``), the CLI prints nothing.
           A caller may therefore test presence, never truthiness of a null.

        Returns:
            List of matching entries with snippets and rank
        """
        # Observability trace — a caller may pass a dict to receive the
        # mode/fallback/latency decisions; we always keep a local one so the
        # structured log line below is emitted on every search. Held locally
        # (not on self) because the service instance is shared across requests
        # on the server/MCP side.
        tr: dict[str, Any] = trace if trace is not None else {}

        # Validate `limit` once, here, rather than letting whatever arithmetic
        # reaches it first decide the error. `limit=None` used to surface as a
        # bare TypeError from `limit * 3` deep inside the hybrid leg -- and,
        # with a filter active, the old dropped-leg rescue caught it and
        # reported "this backend cannot filter". `limit=-1` reached SQLite and
        # came back as OperationalError, which the REST layer turns into HTTP
        # 400 SEARCH_FAILED. Both are the caller's mistake; say so, and name
        # the value (#56).
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError(f"limit must be a positive integer, got {limit!r}")

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
                fetch = limit * 4 if kb_names is not None else limit
                results = self._semantic_search(
                    query,
                    kb_name,
                    fetch,
                    offset=offset,
                    filters=self._leg_filters(
                        entry_type=entry_type,
                        tags=tags,
                        date_from=date_from,
                        date_to=date_to,
                        fips=fips,
                        state=state,
                        status=status,
                        include_archived=include_archived,
                    ),
                    warnings=warnings,
                )
                results = self._restrict(results, kb_names, limit)
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
                    limit * 4 if kb_names is not None else limit,
                    offset,
                    sanitize,
                    expanded_query=expanded_query,
                    fips=fips,
                    state=state,
                    status=status,
                    trace=tr,
                    warnings=warnings,
                    include_archived=include_archived,
                )
                results = self._restrict(results, kb_names, limit)
            else:
                # Default: keyword search
                kw_query = expanded_query
                if sanitize:
                    kw_query = self.sanitize_fts_query(kw_query)

                def _run(q: str) -> list[dict[str, Any]]:
                    return self._db_search(
                        query=q,
                        kb_name=kb_name,
                        kb_names=kb_names,
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
                        logger.debug("keyword search 0 hits; retrying OR-relaxed: %r", relaxed)
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
        filters: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Pure semantic vector search, with the keyword leg's filters applied.

        ``filters`` goes to the backend's ``search_semantic``, which applies it
        inside the KNN query. Whether a backend can do that is a *declared*
        capability, ``FILTERED_SEMANTIC``, checked before the leg runs: a
        backend that does not declare it never sees the filter, and the leg is
        dropped with the offending filters named in ``warnings`` (#56 — a
        filter is honoured or reported, never silently dropped).

        Declared rather than probed on purpose. An earlier version called the
        backend and read a ``TypeError`` as "cannot filter", but that wraps the
        whole vector leg — embedding the query, the backend call, snippet
        generation — so any genuine ``TypeError`` anywhere inside it was
        relabelled as a missing feature and turned into a silently empty
        semantic leg. Bugs now propagate.
        """
        from .embedding_service import EmbeddingService, is_available

        if not is_available() or not self.db.vec_available:
            return []

        svc = EmbeddingService(self.db)
        if not svc.has_embeddings():
            # ADR-0035 §5. Under "writes are eventually-embedded" this is the
            # ordinary state of a KB nobody has embedded yet, and an empty
            # result set is indistinguishable from "searched, found nothing".
            # Say which it is and name the command that fixes it -- without
            # this, a fresh install's semantic search is a silent [].
            #
            # Only when the KB has entries: on a genuinely empty index the
            # answer is `pyrite index build`, and sending someone to `index
            # embed` would be the wrong advice confidently given.
            if warnings is not None and self._index_has_entries(kb_name):
                warnings.append(
                    "semantic leg skipped: no embeddings exist for this index yet, so "
                    "only the keyword leg ran; run `pyrite index embed` to build them"
                )
            return []

        # ``include_archived`` is a default *exclusion*, not a value filter: it
        # must reach the backend even when False (that is when it does its
        # work), and it is not what a warning should name — the caller did not
        # ask for it. Every other filter is sent only when set.
        supplied = {k: v for k, v in (filters or {}).items() if k != "include_archived" and v}
        active = dict(supplied)
        if filters and "include_archived" in filters:
            active["include_archived"] = filters["include_archived"]

        if active and not self._backend_filters_semantic():
            named = sorted(supplied) or ["the archived-entry exclusion"]
            if warnings is not None:
                warnings.append(
                    "semantic leg dropped: this backend cannot filter vector search by "
                    + ", ".join(named)
                    + "; results come from the keyword leg only"
                )
            logger.warning("semantic leg dropped — backend cannot filter by %s", named)
            return []

        # sqlite-vec KNN doesn't support SQL OFFSET, so fetch limit+offset
        # and slice in Python
        results = svc.search_similar(
            query,
            kb_name=kb_name,
            limit=limit + offset,
            max_distance=max_distance,
            **active,
        )
        return results[offset:]

    @staticmethod
    def _leg_filters(
        *,
        entry_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        fips: str | None = None,
        state: str | None = None,
        status: str | None = None,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        """The one filter set every leg receives (#56).

        Built in one place so the semantic and hybrid call sites cannot drift
        apart — a filter present in one dict and missing from the other is
        exactly the class of bug this change exists to close. Adding a filter
        to search means adding it here, and both legs get it.
        """
        return {
            "entry_type": entry_type,
            "tags": tags,
            "date_from": date_from,
            "date_to": date_to,
            "fips": fips,
            "state": state,
            "status": status,
            "include_archived": include_archived,
        }

    def _index_has_entries(self, kb_name: str | None = None) -> bool:
        """Is there anything indexed that *could* have been embedded?

        Distinguishes "indexed but not embedded" (tell them `pyrite index
        embed`) from "nothing indexed at all" (they need `pyrite index build`,
        and an embed warning would send them the wrong way). Best-effort: a
        backend that cannot answer cheaply gets the benefit of the doubt,
        because a missing warning is a smaller harm than a wrong one.
        """
        kwargs = {"kb_name": kb_name} if kb_name else {}
        try:
            return self.db.count_entries(**kwargs) > 0
        except Exception:
            logger.debug("Could not count entries for the embed warning", exc_info=True)
            return False

    def _backend_filters_semantic(self) -> bool:
        """Does this backend's vector leg honour the keyword leg's filters?

        Read from the backend's declared capability set. A backend that
        declares nothing (or is a stand-in that never declared) is assumed not
        to filter: the safe reading is to drop the leg and say so, never to
        return rows that violate the caller's filter.
        """
        from ..storage.backends.capabilities import BackendCapability

        declared = getattr(self.db.backend, "capabilities", set()) or set()
        return BackendCapability.FILTERED_SEMANTIC in declared

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
        warnings: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search using Reciprocal Rank Fusion (RRF).

        Combines FTS5 keyword results with vector similarity results.
        Falls back to keyword-only if no embeddings exist.

        Both legs take the same filter set: the fused result is only as
        trustworthy as its least-filtered leg (#56).
        """
        # Get keyword results — use expanded query for FTS5 leg if available
        # Fetch enough candidates from each leg to cover offset + limit after fusion
        fetch_size = max(limit * 2, offset + limit)
        fts_query = expanded_query if expanded_query else query
        kw_query = self.sanitize_fts_query(fts_query) if sanitize else fts_query
        keyword_results = self._db_search(
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
            include_archived=include_archived,
        )

        # Try to get semantic results — filtered on the vector leg itself, so
        # the fused set can never contain an entry the caller's filter excluded.
        semantic_results = self._semantic_search(
            query,
            kb_name,
            limit=fetch_size,
            filters=self._leg_filters(
                entry_type=entry_type,
                tags=tags,
                date_from=date_from,
                date_to=date_to,
                fips=fips,
                state=state,
                status=status,
                include_archived=include_archived,
            ),
            warnings=warnings,
        )

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
