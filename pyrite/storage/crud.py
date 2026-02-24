"""
Entry CRUD operations.

Mixin class for insert, update, delete, and get operations on entries.
upsert_entry is split into sub-functions for maintainability.
"""

import json
from typing import Any


class CRUDMixin:
    """Entry create, read, update, delete operations."""

    def upsert_entry(self, entry_data: dict[str, Any]) -> None:
        """Insert or update an entry. Extension fields go into metadata JSON."""
        entry_id = entry_data.get("id")
        kb_name = entry_data.get("kb_name")

        self._upsert_entry_main(entry_id, kb_name, entry_data)
        self._sync_tags(entry_id, kb_name, entry_data.get("tags", []))
        self._sync_sources(entry_id, kb_name, entry_data.get("sources", []))
        self._sync_links(entry_id, kb_name, entry_data.get("links", []))
        self._sync_entry_refs(entry_id, kb_name, entry_data)

        self._raw_conn.commit()

    def _upsert_entry_main(self, entry_id: str, kb_name: str, entry_data: dict[str, Any]) -> None:
        """Insert or update the core entry row."""
        metadata = entry_data.get("metadata", {})
        metadata_json = json.dumps(metadata) if metadata else "{}"

        self._raw_conn.execute(
            """
            INSERT INTO entry (
                id, kb_name, entry_type, title, body, summary, file_path,
                date, importance, status, location, metadata,
                created_at, updated_at, indexed_at,
                created_by, modified_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            ON CONFLICT(id, kb_name) DO UPDATE SET
                entry_type = excluded.entry_type,
                title = excluded.title,
                body = excluded.body,
                summary = excluded.summary,
                file_path = excluded.file_path,
                date = excluded.date,
                importance = excluded.importance,
                status = excluded.status,
                location = excluded.location,
                metadata = excluded.metadata,
                updated_at = excluded.updated_at,
                indexed_at = CURRENT_TIMESTAMP,
                created_by = COALESCE(entry.created_by, excluded.created_by),
                modified_by = COALESCE(excluded.modified_by, entry.modified_by)
            """,
            (
                entry_id,
                kb_name,
                entry_data.get("entry_type"),
                entry_data.get("title"),
                entry_data.get("body"),
                entry_data.get("summary"),
                entry_data.get("file_path"),
                entry_data.get("date"),
                entry_data.get("importance"),
                entry_data.get("status"),
                entry_data.get("location"),
                metadata_json,
                entry_data.get("created_at"),
                entry_data.get("updated_at"),
                entry_data.get("created_by"),
                entry_data.get("modified_by"),
            ),
        )

    def _sync_tags(self, entry_id: str, kb_name: str, tags: list[str]) -> None:
        """Replace all tags for an entry."""
        self._raw_conn.execute(
            "DELETE FROM entry_tag WHERE entry_id = ? AND kb_name = ?",
            (entry_id, kb_name),
        )
        for tag_name in tags:
            self._raw_conn.execute("INSERT OR IGNORE INTO tag (name) VALUES (?)", (tag_name,))
            tag_row = self._raw_conn.execute(
                "SELECT id FROM tag WHERE name = ?", (tag_name,)
            ).fetchone()
            tag_id = tag_row[0]
            self._raw_conn.execute(
                "INSERT INTO entry_tag (entry_id, kb_name, tag_id) VALUES (?, ?, ?)",
                (entry_id, kb_name, tag_id),
            )

    def _sync_sources(self, entry_id: str, kb_name: str, sources: list[dict[str, Any]]) -> None:
        """Replace all sources for an entry."""
        self._raw_conn.execute(
            "DELETE FROM source WHERE entry_id = ? AND kb_name = ?",
            (entry_id, kb_name),
        )
        for src in sources:
            self._raw_conn.execute(
                """
                INSERT INTO source (entry_id, kb_name, title, url, outlet, date, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    kb_name,
                    src.get("title", ""),
                    src.get("url", ""),
                    src.get("outlet", ""),
                    src.get("date", ""),
                    1 if src.get("verified") else 0,
                ),
            )

    def _sync_links(self, entry_id: str, kb_name: str, links: list[dict[str, Any]]) -> None:
        """Replace all outgoing links for an entry."""
        self._raw_conn.execute(
            "DELETE FROM link WHERE source_id = ? AND source_kb = ?",
            (entry_id, kb_name),
        )
        for link in links:
            from ..schema import get_inverse_relation

            relation = link.get("relation", "related_to")
            inverse = get_inverse_relation(relation)
            target_kb = link.get("kb", kb_name)
            self._raw_conn.execute(
                """
                INSERT INTO link (source_id, source_kb, target_id, target_kb,
                                  relation, inverse_relation, note)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    kb_name,
                    link.get("target"),
                    target_kb,
                    relation,
                    inverse,
                    link.get("note", ""),
                ),
            )

    def _sync_entry_refs(self, entry_id: str, kb_name: str, entry_data: dict) -> None:
        """Sync object-ref fields into entry_ref table."""
        self._raw_conn.execute(
            "DELETE FROM entry_ref WHERE source_id = ? AND source_kb = ?",
            (entry_id, kb_name),
        )
        refs = entry_data.get("_refs", [])
        for ref in refs:
            self._raw_conn.execute(
                """INSERT INTO entry_ref (source_id, source_kb, target_id, target_kb,
                   field_name, target_type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry_id,
                    kb_name,
                    ref["target_id"],
                    ref.get("target_kb", kb_name),
                    ref["field_name"],
                    ref.get("target_type"),
                ),
            )

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        """Delete an entry. Returns True if deleted."""
        result = self._raw_conn.execute(
            "DELETE FROM entry WHERE id = ? AND kb_name = ?", (entry_id, kb_name)
        )
        self._raw_conn.commit()
        return result.rowcount > 0

    def get_entry(self, entry_id: str, kb_name: str) -> dict[str, Any] | None:
        """Get a single entry with all metadata."""
        row = self._raw_conn.execute(
            "SELECT * FROM entry WHERE id = ? AND kb_name = ?", (entry_id, kb_name)
        ).fetchone()

        if not row:
            return None

        entry = dict(row)
        entry["tags"] = self._get_entry_tags(entry_id, kb_name)
        entry["sources"] = self._get_entry_sources(entry_id, kb_name)
        entry["links"] = self._get_entry_links(entry_id, kb_name)
        return entry

    def _get_entry_tags(self, entry_id: str, kb_name: str) -> list[str]:
        """Get tag names for an entry."""
        return [
            r["name"]
            for r in self._raw_conn.execute(
                """
                SELECT t.name FROM tag t
                JOIN entry_tag et ON t.id = et.tag_id
                WHERE et.entry_id = ? AND et.kb_name = ?
                """,
                (entry_id, kb_name),
            ).fetchall()
        ]

    def _get_entry_sources(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get sources for an entry."""
        return [
            dict(r)
            for r in self._raw_conn.execute(
                "SELECT * FROM source WHERE entry_id = ? AND kb_name = ?",
                (entry_id, kb_name),
            ).fetchall()
        ]

    def _get_entry_links(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get outgoing links for an entry."""
        return [
            dict(r)
            for r in self._raw_conn.execute(
                "SELECT target_id, target_kb, relation, note "
                "FROM link WHERE source_id = ? AND source_kb = ?",
                (entry_id, kb_name),
            ).fetchall()
        ]

    def list_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List entries with pagination, optionally filtered by KB and/or entry type."""
        sql = "SELECT * FROM entry WHERE 1=1"
        params: list[str | int] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)
        if entry_type:
            sql += " AND entry_type = ?"
            params.append(entry_type)
        sql += " ORDER BY updated_at DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._raw_conn.execute(sql, params).fetchall()

        entries = []
        for row in rows:
            entry = dict(row)
            entry["tags"] = self._get_entry_tags(entry["id"], entry["kb_name"])
            entries.append(entry)
        return entries

    def count_entries(self, kb_name: str | None = None, entry_type: str | None = None) -> int:
        """Count entries, optionally filtered by KB and/or entry type."""
        sql = "SELECT COUNT(*) FROM entry WHERE 1=1"
        params: list[str] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)
        if entry_type:
            sql += " AND entry_type = ?"
            params.append(entry_type)
        row = self._raw_conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    def get_entries_for_indexing(self, kb_name: str) -> list[dict[str, Any]]:
        """Get entry id, file_path, indexed_at for incremental indexing."""
        rows = self._raw_conn.execute(
            "SELECT id, file_path, indexed_at FROM entry WHERE kb_name = ?",
            (kb_name,),
        ).fetchall()
        return [dict(r) for r in rows]
