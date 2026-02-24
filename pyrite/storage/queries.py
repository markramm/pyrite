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

    def get_graph_data(
        self,
        center: str | None = None,
        center_kb: str | None = None,
        kb_name: str | None = None,
        entry_type: str | None = None,
        depth: int = 2,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Multi-hop BFS graph traversal returning nodes and edges.

        Args:
            center: Optional entry ID to start from. If None, returns all linked entries.
            center_kb: KB name for center entry.
            kb_name: Filter to entries in this KB.
            entry_type: Filter to this entry type.
            depth: Max hops from center (1-3, default 2).
            limit: Max nodes to return (default 500).

        Returns:
            {"nodes": [...], "edges": [...]}
        """
        depth = max(1, min(3, depth))
        nodes: dict[tuple[str, str], dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        edge_set: set[tuple[str, str, str, str]] = set()

        if center and center_kb:
            # BFS from center
            row = self._raw_conn.execute(
                "SELECT id, kb_name, title, entry_type FROM entry WHERE id = ? AND kb_name = ?",
                (center, center_kb),
            ).fetchone()
            if not row:
                return {"nodes": [], "edges": []}
            nodes[(row["id"], row["kb_name"])] = dict(row)

            frontier = [(center, center_kb)]
            for _hop in range(depth):
                if not frontier or len(nodes) >= limit:
                    break
                next_frontier: list[tuple[str, str]] = []
                for eid, ekb in frontier:
                    if len(nodes) >= limit:
                        break
                    # Outgoing links
                    out_rows = self._raw_conn.execute(
                        """SELECT l.target_id, l.target_kb, l.relation,
                                  e.title, e.entry_type
                           FROM link l
                           LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
                           WHERE l.source_id = ? AND l.source_kb = ?""",
                        (eid, ekb),
                    ).fetchall()
                    for r in out_rows:
                        if len(nodes) >= limit:
                            break
                        tid, tkb = r["target_id"], r["target_kb"]
                        if kb_name and tkb != kb_name:
                            continue
                        if entry_type and r["entry_type"] and r["entry_type"] != entry_type:
                            continue
                        edge_key = (eid, ekb, tid, tkb)
                        if edge_key not in edge_set:
                            edge_set.add(edge_key)
                            edges.append({
                                "source_id": eid,
                                "source_kb": ekb,
                                "target_id": tid,
                                "target_kb": tkb,
                                "relation": r["relation"],
                            })
                        if (tid, tkb) not in nodes:
                            nodes[(tid, tkb)] = {
                                "id": tid,
                                "kb_name": tkb,
                                "title": r["title"] or tid,
                                "entry_type": r["entry_type"] or "unknown",
                            }
                            next_frontier.append((tid, tkb))

                    # Incoming links
                    in_rows = self._raw_conn.execute(
                        """SELECT l.source_id, l.source_kb, l.relation,
                                  e.title, e.entry_type
                           FROM link l
                           JOIN entry e ON l.source_id = e.id AND l.source_kb = e.kb_name
                           WHERE l.target_id = ? AND l.target_kb = ?""",
                        (eid, ekb),
                    ).fetchall()
                    for r in in_rows:
                        if len(nodes) >= limit:
                            break
                        sid, skb = r["source_id"], r["source_kb"]
                        if kb_name and skb != kb_name:
                            continue
                        if entry_type and r["entry_type"] != entry_type:
                            continue
                        edge_key = (sid, skb, eid, ekb)
                        if edge_key not in edge_set:
                            edge_set.add(edge_key)
                            edges.append({
                                "source_id": sid,
                                "source_kb": skb,
                                "target_id": eid,
                                "target_kb": ekb,
                                "relation": r["relation"],
                            })
                        if (sid, skb) not in nodes:
                            nodes[(sid, skb)] = {
                                "id": sid,
                                "kb_name": skb,
                                "title": r["title"] or sid,
                                "entry_type": r["entry_type"] or "unknown",
                            }
                            next_frontier.append((sid, skb))

                frontier = next_frontier
        else:
            # No center: return all linked entries
            sql = """
                SELECT e.id, e.kb_name, e.title, e.entry_type
                FROM entry e
                WHERE e.id IN (SELECT source_id FROM link)
                   OR e.id IN (SELECT target_id FROM link)
            """
            params: list[Any] = []
            if kb_name:
                sql += " AND e.kb_name = ?"
                params.append(kb_name)
            if entry_type:
                sql += " AND e.entry_type = ?"
                params.append(entry_type)
            sql += " LIMIT ?"
            params.append(limit)

            for r in self._raw_conn.execute(sql, params).fetchall():
                nodes[(r["id"], r["kb_name"])] = dict(r)

            # Get edges between collected nodes
            if nodes:
                link_rows = self._raw_conn.execute(
                    "SELECT source_id, source_kb, target_id, target_kb, relation FROM link"
                ).fetchall()
                for r in link_rows:
                    src = (r["source_id"], r["source_kb"])
                    tgt = (r["target_id"], r["target_kb"])
                    if src in nodes and tgt in nodes:
                        edges.append(dict(r))

        # Compute link_count for each node
        node_list = []
        for node in nodes.values():
            count = 0
            for e in edges:
                if (e["source_id"] == node["id"] and e["source_kb"] == node["kb_name"]) or \
                   (e["target_id"] == node["id"] and e["target_kb"] == node["kb_name"]):
                    count += 1
            node["link_count"] = count
            node_list.append(node)

        return {"nodes": node_list, "edges": edges}

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

    # =========================================================================
    # Object Refs
    # =========================================================================

    def get_refs_from(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries this entry references via object-ref fields."""
        rows = self._raw_conn.execute(
            """SELECT r.target_id as id, r.target_kb as kb_name, r.field_name, r.target_type,
                      e.title, e.entry_type
               FROM entry_ref r
               LEFT JOIN entry e ON r.target_id = e.id AND r.target_kb = e.kb_name
               WHERE r.source_id = ? AND r.source_kb = ?""",
            (entry_id, kb_name),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_refs_to(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that reference this entry via object-ref fields."""
        rows = self._raw_conn.execute(
            """SELECT r.source_id as id, r.source_kb as kb_name, r.field_name, r.target_type,
                      e.title, e.entry_type
               FROM entry_ref r
               JOIN entry e ON r.source_id = e.id AND r.source_kb = e.kb_name
               WHERE r.target_id = ? AND r.target_kb = ?""",
            (entry_id, kb_name),
        ).fetchall()
        return [dict(r) for r in rows]

    # =========================================================================
    # Settings
    # =========================================================================

    def get_setting(self, key: str) -> str | None:
        """Get a setting value by key."""
        row = self._raw_conn.execute(
            "SELECT value FROM setting WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value (upsert)."""
        self._raw_conn.execute(
            """INSERT INTO setting (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET
               value = excluded.value, updated_at = CURRENT_TIMESTAMP""",
            (key, value),
        )
        self._raw_conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings as a dict."""
        rows = self._raw_conn.execute("SELECT key, value FROM setting").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def delete_setting(self, key: str) -> bool:
        """Delete a setting. Returns True if deleted."""
        result = self._raw_conn.execute("DELETE FROM setting WHERE key = ?", (key,))
        self._raw_conn.commit()
        return result.rowcount > 0

    # =========================================================================
    # Tag hierarchy
    # =========================================================================

    def get_tag_tree(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Build hierarchical tag tree from /-separated tags.

        Returns list of tree nodes: {name, full_path, count, children: [...]}
        """
        flat_tags = self.get_all_tags(kb_name)

        root_children: list[dict[str, Any]] = []
        node_map: dict[str, dict[str, Any]] = {}

        for tag_name, count in sorted(flat_tags, key=lambda t: t[0]):
            parts = tag_name.split("/")
            for i, part in enumerate(parts):
                full_path = "/".join(parts[: i + 1])
                if full_path not in node_map:
                    node: dict[str, Any] = {
                        "name": part,
                        "full_path": full_path,
                        "count": 0,
                        "children": [],
                    }
                    node_map[full_path] = node
                    if i == 0:
                        root_children.append(node)
                    else:
                        parent_path = "/".join(parts[:i])
                        node_map[parent_path]["children"].append(node)
            # Set count on the leaf (exact tag)
            if tag_name in node_map:
                node_map[tag_name]["count"] = count

        return root_children

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by tag prefix (parent tag includes children)."""
        sql = """
            SELECT DISTINCT e.* FROM entry e
            JOIN entry_tag et ON e.id = et.entry_id AND e.kb_name = et.kb_name
            JOIN tag t ON et.tag_id = t.id
            WHERE (t.name = ? OR t.name LIKE ?)
        """
        params: list[Any] = [prefix, prefix + "/%"]

        if kb_name:
            sql += " AND e.kb_name = ?"
            params.append(kb_name)

        sql += " ORDER BY e.date DESC, e.title LIMIT ?"
        params.append(limit)

        rows = self._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
