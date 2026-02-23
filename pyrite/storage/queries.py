"""
Search, graph, analytics, and timeline queries.

Mixin class for read-only query operations.
"""

from typing import Any


class QueryMixin:
    """Search, graph traversal, analytics, and timeline queries."""

    # =========================================================================
    # Full-text and filtered search
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
    ) -> list[dict[str, Any]]:
        """Full-text search across entries using FTS5."""
        sql = """
            SELECT
                e.*,
                snippet(entry_fts, 4, '<mark>', '</mark>', '...', 32) as snippet,
                bm25(entry_fts) as rank
            FROM entry_fts
            JOIN entry e ON entry_fts.rowid = e.rowid
            WHERE entry_fts MATCH ?
        """
        params: list[Any] = [query]

        if kb_name:
            sql += " AND e.kb_name = ?"
            params.append(kb_name)

        if entry_type:
            sql += " AND e.entry_type = ?"
            params.append(entry_type)

        if date_from:
            sql += " AND e.date >= ?"
            params.append(date_from)

        if date_to:
            sql += " AND e.date <= ?"
            params.append(date_to)

        if tags:
            tag_placeholders = ",".join(["?"] * len(tags))
            sql += f"""
                AND e.id IN (
                    SELECT et.entry_id FROM entry_tag et
                    JOIN tag t ON et.tag_id = t.id
                    WHERE t.name IN ({tag_placeholders})
                    GROUP BY et.entry_id, et.kb_name
                    HAVING COUNT(DISTINCT t.name) = ?
                )
            """
            params.extend(tags)
            params.append(len(tags))

        sql += " ORDER BY rank LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_by_tag(
        self, tag: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by tag."""
        sql = """
            SELECT e.* FROM entry e
            JOIN entry_tag et ON e.id = et.entry_id AND e.kb_name = et.kb_name
            JOIN tag t ON et.tag_id = t.id
            WHERE t.name = ?
        """
        params: list[Any] = [tag]

        if kb_name:
            sql += " AND e.kb_name = ?"
            params.append(kb_name)

        sql += " ORDER BY e.date DESC, e.title LIMIT ?"
        params.append(limit)

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def search_by_date_range(
        self,
        date_from: str,
        date_to: str,
        kb_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search events within a date range."""
        sql = """
            SELECT * FROM entry
            WHERE date >= ? AND date <= ?
        """
        params: list[Any] = [date_from, date_to]

        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        sql += " ORDER BY date ASC LIMIT ?"
        params.append(limit)

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # =========================================================================
    # Graph queries (links)
    # =========================================================================

    def get_backlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that link TO this entry."""
        rows = self._raw_conn.execute(
            """
            SELECT e.id, e.kb_name, e.title, e.entry_type,
                   l.inverse_relation as relation, l.note
            FROM link l
            JOIN entry e ON l.source_id = e.id AND l.source_kb = e.kb_name
            WHERE l.target_id = ? AND l.target_kb = ?
            """,
            (entry_id, kb_name),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that this entry links TO."""
        rows = self._raw_conn.execute(
            """
            SELECT l.target_id as id, l.target_kb as kb_name,
                   e.title, e.entry_type, l.relation, l.note
            FROM link l
            LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
            WHERE l.source_id = ? AND l.source_kb = ?
            """,
            (entry_id, kb_name),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_related(self, entry_id: str, kb_name: str, depth: int = 1) -> list[dict[str, Any]]:
        """Get related entries (both directions) up to N hops."""
        backlinks = self.get_backlinks(entry_id, kb_name)
        outlinks = self.get_outlinks(entry_id, kb_name)

        related = []
        seen = set()

        for link in backlinks + outlinks:
            key = (link.get("id"), link.get("kb_name"))
            if key not in seen and key != (entry_id, kb_name):
                seen.add(key)
                related.append(link)

        return related

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_all_tags(self, kb_name: str | None = None) -> list[tuple[str, int]]:
        """Get all tags with counts."""
        if kb_name:
            rows = self._raw_conn.execute(
                """
                SELECT t.name, COUNT(*) as count
                FROM tag t
                JOIN entry_tag et ON t.id = et.tag_id
                WHERE et.kb_name = ?
                GROUP BY t.name
                ORDER BY count DESC
                """,
                (kb_name,),
            ).fetchall()
        else:
            rows = self._raw_conn.execute("""
                SELECT t.name, COUNT(*) as count
                FROM tag t
                JOIN entry_tag et ON t.id = et.tag_id
                GROUP BY t.name
                ORDER BY count DESC
            """).fetchall()
        return [(r["name"], r["count"]) for r in rows]

    def get_most_linked(self, kb_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get entries with most incoming links (most referenced)."""
        sql = """
            SELECT e.id, e.kb_name, e.title, e.entry_type,
                   COUNT(l.id) as link_count
            FROM entry e
            LEFT JOIN link l ON e.id = l.target_id AND e.kb_name = l.target_kb
        """
        params: list[Any] = []

        if kb_name:
            sql += " WHERE e.kb_name = ?"
            params.append(kb_name)

        sql += " GROUP BY e.id, e.kb_name ORDER BY link_count DESC LIMIT ?"
        params.append(limit)

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get entries with no links (neither incoming nor outgoing)."""
        sql = """
            SELECT e.id, e.kb_name, e.title, e.entry_type
            FROM entry e
            WHERE e.id NOT IN (
                SELECT source_id FROM link WHERE source_kb = e.kb_name
            )
            AND e.id NOT IN (
                SELECT target_id FROM link WHERE target_kb = e.kb_name
            )
        """
        params: list[Any] = []

        if kb_name:
            sql += " AND e.kb_name = ?"
            params.append(kb_name)

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_timeline(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        min_importance: int = 1,
        kb_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get timeline events ordered by date."""
        sql = """
            SELECT id, kb_name, title, date, importance, location, summary
            FROM entry
            WHERE date IS NOT NULL AND importance >= ?
        """
        params: list[Any] = [min_importance]

        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        if date_from:
            sql += " AND date >= ?"
            params.append(date_from)

        if date_to:
            sql += " AND date <= ?"
            params.append(date_to)

        sql += " ORDER BY date ASC"

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_global_counts(self) -> dict[str, int]:
        """Get global tag and link counts."""
        tag_row = self._raw_conn.execute("SELECT COUNT(*) FROM tag").fetchone()
        link_row = self._raw_conn.execute("SELECT COUNT(*) FROM link").fetchone()
        return {
            "total_tags": tag_row[0] if tag_row else 0,
            "total_links": link_row[0] if link_row else 0,
        }

    def get_tags_as_dicts(
        self, kb_name: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get tags with counts as dicts, optionally filtered by KB."""
        if kb_name:
            rows = self._raw_conn.execute(
                """
                SELECT t.name, COUNT(*) as count
                FROM tag t
                JOIN entry_tag et ON t.id = et.tag_id
                WHERE et.kb_name = ?
                GROUP BY t.name
                ORDER BY count DESC
                LIMIT ?
                """,
                (kb_name, limit),
            ).fetchall()
        else:
            rows = self._raw_conn.execute(
                """
                SELECT t.name, COUNT(*) as count
                FROM tag t
                JOIN entry_tag et ON t.id = et.tag_id
                GROUP BY t.name
                ORDER BY count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [{"name": r["name"], "count": r["count"]} for r in rows]
