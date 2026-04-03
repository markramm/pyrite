"""
Link Discovery Service — cross-KB link suggestions, neighbor discovery, orphan detection.

Extracted from CLI link_commands to avoid layer inversions (MCP/API importing CLI code).
All methods return structured data (lists of dicts). Formatting is left to callers.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ..config import PyriteConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class LinkDiscoveryService:
    """Cross-KB link discovery, suggestion, and gap analysis."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_suggest_query(entry: dict) -> str:
        """Build an FTS5 OR query from an entry's title words and tags.

        Uses OR to find entries sharing *any* term, which gives broader recall
        and lets FTS5 rank by overlap.
        """
        tokens: list[str] = []
        title = entry.get("title", "")
        if title:
            tokens.extend(w for w in re.split(r"\W+", title) if w and len(w) > 2)
        tags = entry.get("tags", [])
        if tags:
            tokens.extend(t for t in tags if t)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for t in tokens:
            lower = t.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(t)
        return " OR ".join(unique)

    # ------------------------------------------------------------------
    # suggest_links — single-entry keyword-based suggestion
    # ------------------------------------------------------------------

    def suggest_links(
        self,
        entry_id: str,
        kb_name: str,
        target_kb: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Find entries related to the given entry using FTS5 keyword search.

        Returns a list of candidate dicts with id, kb_name, title, entry_type,
        score, and snippet.
        """
        from .kb_service import KBService
        from .search_service import SearchService

        svc = KBService(self.config, self.db)
        entry = svc.get_entry(entry_id, kb_name=kb_name)
        if entry is None:
            return []

        query = self.build_suggest_query(entry)
        if not query.strip():
            return []

        search_svc = SearchService(self.db, settings=self.config.settings)
        search_kb = target_kb or kb_name

        # Fetch extra results so we can filter out self and existing links
        raw_results = search_svc.search(
            query=query,
            kb_name=search_kb,
            limit=limit + 20,
            mode="keyword",
        )

        # Collect existing link targets to exclude
        existing_targets = set()
        for link in entry.get("outlinks", []) or []:
            existing_targets.add(link.get("id", ""))
        for link in entry.get("links", []) or []:
            existing_targets.add(link.get("target_id") or link.get("target", ""))

        candidates = []
        for r in raw_results:
            rid = r.get("id", "")
            if rid == entry_id:
                continue
            if rid in existing_targets:
                continue
            candidates.append(
                {
                    "id": rid,
                    "kb_name": r.get("kb_name", search_kb),
                    "title": r.get("title", ""),
                    "entry_type": r.get("entry_type", ""),
                    "score": round(r.get("rank", 0.0), 4),
                    "snippet": (r.get("snippet") or "")[:150],
                }
            )
            if len(candidates) >= limit:
                break

        return candidates

    # ------------------------------------------------------------------
    # discover_neighbors — cross-KB semantic neighbor discovery
    # ------------------------------------------------------------------

    def discover_neighbors(
        self,
        entry_id: str,
        kb_name: str,
        target_kb: str | None = None,
        limit: int = 10,
        mode: str = "keyword",
        exclude_linked: bool = True,
    ) -> list[dict]:
        """Find semantically similar entries in other KBs, optionally excluding already-linked.

        Supports keyword, semantic, and hybrid modes. Falls back to keyword
        if semantic embeddings are not available.
        """
        from .kb_service import KBService
        from .search_service import SearchService

        svc = KBService(self.config, self.db)
        entry = svc.get_entry(entry_id, kb_name=kb_name)
        if entry is None:
            return []

        # Build search query from entry content
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        tags = entry.get("tags", [])

        if mode in ("semantic", "hybrid"):
            query_parts = [title]
            if summary:
                query_parts.append(summary[:200])
            query = " ".join(query_parts)
        else:
            # Keyword: OR-joined tokens
            tokens: list[str] = []
            if title:
                tokens.extend(w for w in re.split(r"\W+", title) if w and len(w) > 2)
            if tags:
                tokens.extend(t for t in tags if t)
            seen: set[str] = set()
            unique: list[str] = []
            for t in tokens:
                lower = t.lower()
                if lower not in seen:
                    seen.add(lower)
                    unique.append(t)
            query = " OR ".join(unique)

        if not query.strip():
            return []

        # Fall back to keyword if semantic unavailable
        actual_mode = mode
        if mode in ("semantic", "hybrid"):
            try:
                from .embedding_service import is_available

                if not is_available() or not getattr(self.db, "backend", None) or not getattr(self.db.backend, "vec_available", False):
                    actual_mode = "keyword"
            except (ImportError, AttributeError):
                actual_mode = "keyword"

        search_svc = SearchService(self.db, settings=self.config.settings)

        raw_results = search_svc.search(
            query=query,
            kb_name=target_kb,
            limit=limit + 30,
            mode=actual_mode,
        )

        # Collect existing link targets to exclude
        existing_targets: set[str] = set()
        if exclude_linked:
            for link in entry.get("outlinks", []) or []:
                existing_targets.add(link.get("id", ""))
            for link in entry.get("links", []) or []:
                existing_targets.add(link.get("target_id") or link.get("target", ""))
            backlinks = self.db.get_backlinks(entry_id, kb_name)
            for bl in backlinks:
                existing_targets.add(bl.get("id", ""))

        candidates = []
        for r in raw_results:
            rid = r.get("id", "")
            r_kb = r.get("kb_name", "")

            if rid == entry_id and r_kb == kb_name:
                continue
            if exclude_linked and rid in existing_targets:
                continue

            if "distance" in r:
                score = round(1.0 - (r["distance"] / 2.0), 4)
            else:
                score = round(r.get("rank", 0.0), 4)

            candidates.append({
                "id": rid,
                "kb_name": r_kb,
                "title": r.get("title", ""),
                "entry_type": r.get("entry_type", ""),
                "score": score,
                "snippet": (r.get("snippet") or r.get("summary") or "")[:150],
            })
            if len(candidates) >= limit:
                break

        return candidates

    # ------------------------------------------------------------------
    # batch_suggest — cross-KB batch comparison
    # ------------------------------------------------------------------

    def batch_suggest(
        self,
        source_kb: str,
        target_kb: str,
        limit_per_entry: int = 3,
        mode: str = "keyword",
        exclude_linked: bool = True,
    ) -> list[dict]:
        """Find all potential cross-KB links between two KBs.

        For each entry in source_kb, runs discover_neighbors against target_kb,
        then deduplicates bidirectional matches and sorts by score.
        """
        from .kb_service import KBService

        svc = KBService(self.config, self.db)
        source_entries = svc.list_entries(kb_name=source_kb, limit=10000)

        all_pairs: list[dict] = []
        seen_pairs: set[tuple[str, ...]] = set()

        for entry in source_entries:
            eid = entry.get("id", "")
            candidates = self.discover_neighbors(
                entry_id=eid,
                kb_name=source_kb,
                target_kb=target_kb,
                limit=limit_per_entry,
                mode=mode,
                exclude_linked=exclude_linked,
            )

            for c in candidates:
                # Deduplicate bidirectional: (A,B) and (B,A) are the same pair
                pair_key = tuple(sorted([eid, c["id"]]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                all_pairs.append({
                    "source_id": eid,
                    "source_title": entry.get("title", ""),
                    "source_type": entry.get("entry_type", ""),
                    "target_id": c["id"],
                    "target_title": c["title"],
                    "target_type": c["entry_type"],
                    "score": c["score"],
                    "snippet": c.get("snippet", ""),
                })

        # Sort by score descending
        all_pairs.sort(key=lambda x: x["score"], reverse=True)
        return all_pairs

    # ------------------------------------------------------------------
    # find_orphans — high-importance entries with few cross-KB links
    # ------------------------------------------------------------------

    def find_orphans(
        self,
        kb_name: str,
        min_importance: int = 5,
        limit: int = 20,
    ) -> list[dict]:
        """Find high-importance entries with few cross-KB links relative to their potential.

        Orphan score = potential_matches - cross_kb_links. High score means
        "should be connected but isn't."
        """
        from .kb_service import KBService

        svc = KBService(self.config, self.db)
        entries = svc.list_entries(kb_name=kb_name, limit=10000)

        candidates: list[dict[str, Any]] = []
        for entry in entries:
            importance = entry.get("importance", 5)
            if importance is None:
                importance = 5
            if importance < min_importance:
                continue

            eid = entry.get("id", "")

            # Count existing cross-KB links
            outlinks = self.db.get_outlinks(eid, kb_name)
            backlinks = self.db.get_backlinks(eid, kb_name)
            cross_kb_links = len([
                link for link in (outlinks + backlinks)
                if link.get("kb_name", kb_name) != kb_name
            ])

            # Count potential cross-KB matches (excluding own KB)
            neighbors = self.discover_neighbors(
                entry_id=eid,
                kb_name=kb_name,
                target_kb=None,  # Search all KBs
                limit=5,
                mode="keyword",
                exclude_linked=True,
            )
            # Only count matches from OTHER KBs
            potential = len([n for n in neighbors if n.get("kb_name") != kb_name])

            orphan_score = potential - cross_kb_links
            if orphan_score <= 0 and potential == 0:
                continue

            candidates.append({
                "id": eid,
                "title": entry.get("title", ""),
                "entry_type": entry.get("entry_type", ""),
                "importance": importance,
                "cross_kb_links": cross_kb_links,
                "potential_matches": potential,
                "orphan_score": orphan_score,
            })

        # Sort by orphan score descending, then by importance descending
        candidates.sort(key=lambda x: (x["orphan_score"], x["importance"]), reverse=True)
        return candidates[:limit]

    # ------------------------------------------------------------------
    # find_asymmetric_links — one-directional cross-KB links
    # ------------------------------------------------------------------

    def find_asymmetric_links(
        self,
        kb_a: str,
        kb_b: str,
    ) -> list[dict]:
        """Find one-directional cross-KB links between two KBs.

        Returns links that exist in one direction (A\u2192B) but not the reverse (B\u2192A).
        """
        # Get all entries in both KBs
        entries_a = self.db.list_entries(kb_name=kb_a, limit=10000)
        entries_b = self.db.list_entries(kb_name=kb_b, limit=10000)

        ids_a = {e["id"] for e in entries_a}
        ids_b = {e["id"] for e in entries_b}

        # Build title lookups
        titles_a = {e["id"]: e.get("title", e["id"]) for e in entries_a}
        titles_b = {e["id"]: e.get("title", e["id"]) for e in entries_b}

        # Collect all cross-KB links as directed pairs
        forward_links: dict[tuple[str, str], str] = {}  # (source, target) -> relation
        reverse_links: dict[tuple[str, str], str] = {}

        # A->B links
        for entry in entries_a:
            eid = entry["id"]
            outlinks = self.db.get_outlinks(eid, kb_a)
            for ol in outlinks:
                if ol.get("kb_name") == kb_b and ol["id"] in ids_b:
                    forward_links[(eid, ol["id"])] = ol.get("relation", "related_to")

        # B->A links
        for entry in entries_b:
            eid = entry["id"]
            outlinks = self.db.get_outlinks(eid, kb_b)
            for ol in outlinks:
                if ol.get("kb_name") == kb_a and ol["id"] in ids_a:
                    reverse_links[(eid, ol["id"])] = ol.get("relation", "related_to")

        # Find asymmetric: exists in forward but not reverse, or vice versa
        results: list[dict] = []

        for (src, tgt), relation in forward_links.items():
            if (tgt, src) not in reverse_links:
                results.append({
                    "source_id": src,
                    "source_kb": kb_a,
                    "source_title": titles_a.get(src, src),
                    "target_id": tgt,
                    "target_kb": kb_b,
                    "target_title": titles_b.get(tgt, tgt),
                    "direction": f"{kb_a} \u2192 {kb_b}",
                    "relation": relation,
                })

        for (src, tgt), relation in reverse_links.items():
            if (tgt, src) not in forward_links:
                results.append({
                    "source_id": src,
                    "source_kb": kb_b,
                    "source_title": titles_b.get(src, src),
                    "target_id": tgt,
                    "target_kb": kb_a,
                    "target_title": titles_a.get(tgt, tgt),
                    "direction": f"{kb_b} \u2192 {kb_a}",
                    "relation": relation,
                })

        return results
