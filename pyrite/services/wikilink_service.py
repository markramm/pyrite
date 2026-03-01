"""
Wikilink Service — resolution, autocomplete, and wanted-page queries.

Extracted from KBService to slim it down. All methods are read-only
and use PyriteDB.execute_sql() for queries.
"""

import logging
from typing import Any

from ..config import PyriteConfig
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class WikilinkService:
    """Wikilink resolution, autocomplete titles, and wanted-page queries."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    def list_entry_titles(
        self,
        kb_name: str | None = None,
        query: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Lightweight listing of entry IDs and titles for wikilink autocomplete."""
        sql = "SELECT id, kb_name, entry_type, title, json_extract(metadata, '$.aliases') as aliases FROM entry WHERE 1=1"
        params: dict[str, Any] = {}

        if kb_name:
            sql += " AND kb_name = :kb_name"
            params["kb_name"] = kb_name
        if query:
            sql += " AND (title LIKE :q1 OR json_extract(metadata, '$.aliases') LIKE :q2)"
            params["q1"] = f"%{query}%"
            params["q2"] = f"%{query}%"

        sql += " ORDER BY title COLLATE NOCASE LIMIT :limit"
        params["limit"] = limit

        return self.db.execute_sql(sql, params)

    def resolve_entry(self, target: str, kb_name: str | None = None) -> dict[str, Any] | None:
        """Resolve a wikilink target to an entry. Supports kb:id format for cross-KB links."""
        # Parse cross-KB format
        actual_target = target
        actual_kb = kb_name
        if ":" in target and not target.startswith("http"):
            prefix, rest = target.split(":", 1)
            # Look up KB by shortname
            kb_by_short = self.config.get_kb_by_shortname(prefix)
            if kb_by_short:
                actual_target = rest
                actual_kb = kb_by_short.name
            elif self.config.get_kb(prefix):
                actual_target = rest
                actual_kb = prefix

        # First pass: exact ID match
        sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE id = :target"
        params: dict[str, Any] = {"target": actual_target}
        if actual_kb:
            sql += " AND kb_name = :kb_name"
            params["kb_name"] = actual_kb
        sql += " LIMIT 1"

        rows = self.db.execute_sql(sql, params)
        if rows:
            return rows[0]

        # Second pass: title match
        sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE title LIKE :target"
        params = {"target": actual_target}
        if actual_kb:
            sql += " AND kb_name = :kb_name"
            params["kb_name"] = actual_kb
        sql += " LIMIT 1"

        rows = self.db.execute_sql(sql, params)
        if rows:
            return rows[0]

        # Third pass: search aliases
        sql = """
            SELECT id, kb_name, entry_type, title FROM entry
            WHERE json_extract(metadata, '$.aliases') LIKE :alias_pattern
        """
        params = {"alias_pattern": f"%{actual_target}%"}
        if actual_kb:
            sql += " AND kb_name = :kb_name"
            params["kb_name"] = actual_kb
        sql += " LIMIT 1"

        rows = self.db.execute_sql(sql, params)
        return rows[0] if rows else None

    def resolve_batch(self, targets: list[str], kb_name: str | None = None) -> dict[str, bool]:
        """Batch-resolve wikilink targets. Supports kb:id format."""
        if not targets:
            return {}
        result: dict[str, bool] = {}

        # Separate cross-KB targets from same-KB targets
        simple_targets = []
        for t in targets:
            if ":" in t and not t.startswith("http"):
                # Resolve cross-KB targets individually
                resolved = self.resolve_entry(t, kb_name)
                result[t] = resolved is not None
            else:
                simple_targets.append(t)

        if simple_targets:
            placeholders = ",".join([f":t{i}" for i in range(len(simple_targets))])
            sql = f"SELECT id FROM entry WHERE id IN ({placeholders})"
            params: dict[str, Any] = {f"t{i}": t for i, t in enumerate(simple_targets)}
            if kb_name:
                sql += " AND kb_name = :kb_name"
                params["kb_name"] = kb_name
            rows = self.db.execute_sql(sql, params)
            existing_ids = {r["id"] for r in rows}
            for t in simple_targets:
                result[t] = t in existing_ids

        return result

    def get_wanted_pages(
        self, kb_name: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get link targets that don't exist as entries (wanted pages)."""
        sql = """
            SELECT l.target_id, l.target_kb, COUNT(*) as ref_count,
                   GROUP_CONCAT(DISTINCT l.source_id) as referenced_by
            FROM link l
            LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
            WHERE e.id IS NULL
        """
        params: dict[str, Any] = {}
        if kb_name:
            sql += " AND l.target_kb = :kb_name"
            params["kb_name"] = kb_name
        sql += " GROUP BY l.target_id, l.target_kb ORDER BY ref_count DESC LIMIT :limit"
        params["limit"] = limit
        return self.db.execute_sql(sql, params)
