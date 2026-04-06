"""
PostgresBackend — SearchBackend implementation backed by PostgreSQL + tsvector + pgvector.

Inherits shared ORM/SQL logic from BaseBackend.  Only overrides:
- ``_exec`` / ``_exec_one`` / ``_exec_scalar`` (SQLAlchemy text() with named params)
- ``_sync_links`` (delete-all-reinsert)
- Full-text search (tsvector/tsquery)
- Embedding operations (pgvector)
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .base_backend import BaseBackend
from ..models import Link

logger = logging.getLogger(__name__)


def ensure_schema(engine) -> None:
    """Create pgvector extension, FTS column, embedding column, and indexes.

    Idempotent — safe to call on every startup.
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("ALTER TABLE entry ADD COLUMN IF NOT EXISTS fts_vector tsvector"))
        conn.execute(text("ALTER TABLE entry ADD COLUMN IF NOT EXISTS embedding vector(384)"))
        # GIN index for FTS
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_entry_fts ON entry USING gin(fts_vector)")
        )
        # IVFFlat index for vector KNN (requires rows to exist; falls back to seq scan if empty)
        # Use HNSW for small corpora — no training needed
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_entry_embedding "
                "ON entry USING hnsw(embedding vector_cosine_ops)"
            )
        )
        # Trigger to auto-update fts_vector on INSERT/UPDATE
        conn.execute(
            text("""
            CREATE OR REPLACE FUNCTION entry_fts_trigger() RETURNS trigger AS $$
            BEGIN
                NEW.fts_vector :=
                    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(NEW.body, '')), 'C');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        )
        conn.execute(
            text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_entry_fts'
                ) THEN
                    CREATE TRIGGER trg_entry_fts
                    BEFORE INSERT OR UPDATE ON entry
                    FOR EACH ROW EXECUTE FUNCTION entry_fts_trigger();
                END IF;
            END $$;
        """)
        )
        conn.commit()


class PostgresBackend(BaseBackend):
    """SearchBackend implementation for PostgreSQL + tsvector + pgvector."""

    def __init__(self, session: Session, engine=None):
        self._session = session
        self._engine = engine

    def close(self) -> None:
        """No-op — connection lifecycle owned by caller."""

    # =====================================================================
    # Raw SQL helpers (SQLAlchemy text() with :named params)
    # =====================================================================

    def _exec(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
        """Execute raw SQL and return all rows as list of dicts."""
        result = self._session.execute(text(sql), params or {})
        try:
            rows = result.fetchall()
            cols = result.keys()
            return [dict(zip(cols, row, strict=True)) for row in rows]
        except Exception:
            return []

    def _exec_one(self, sql: str, params: dict | None = None) -> dict | None:
        """Execute raw SQL and return first row as dict, or None."""
        result = self._session.execute(text(sql), params or {})
        row = result.fetchone()
        if row is None:
            return None
        return dict(zip(result.keys(), row, strict=True))

    def _exec_scalar(self, sql: str, params: dict | None = None):
        """Execute raw SQL and return scalar value."""
        result = self._session.execute(text(sql), params or {})
        row = result.fetchone()
        return row[0] if row else None

    # =====================================================================
    # _sync_links (delete-all-reinsert — Postgres-specific)
    # =====================================================================

    def _sync_links(self, entry_id: str, kb_name: str, links: list[dict[str, Any]]) -> None:
        self._session.query(Link).filter_by(source_id=entry_id, source_kb=kb_name).delete()
        for link in links:
            from ...schema import get_inverse_relation

            relation = link.get("relation", "related_to")
            inverse = get_inverse_relation(relation)
            target_kb = link.get("kb", kb_name)
            self._session.add(
                Link(
                    source_id=entry_id,
                    source_kb=kb_name,
                    target_id=link.get("target"),
                    target_kb=target_kb,
                    relation=relation,
                    inverse_relation=inverse,
                    note=link.get("note", ""),
                )
            )

    # =====================================================================
    # Full-text search (PostgreSQL tsvector/tsquery)
    # =====================================================================

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
        include_archived: bool = False,
        lifecycle: str | None = None,
    ) -> list[dict[str, Any]]:
        # Build the tsquery — plainto_tsquery handles user input safely
        sql = """
            SELECT
                e.id, e.kb_name, e.entry_type, e.title, e.body, e.summary,
                e.file_path, e.date, e.importance, e.status, e.location,
                e.lifecycle, e.metadata, e.created_at, e.updated_at, e.indexed_at,
                e.created_by, e.modified_by,
                ts_headline('english', coalesce(e.body, ''),
                    plainto_tsquery('english', :query),
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=3, MaxWords=32'
                ) as snippet,
                ts_rank(e.fts_vector, plainto_tsquery('english', :query)) as rank
            FROM entry e
            WHERE e.fts_vector @@ plainto_tsquery('english', :query)
        """
        params: dict[str, Any] = {"query": query}

        if lifecycle:
            sql += " AND e.lifecycle = :lifecycle"
            params["lifecycle"] = lifecycle
        elif not include_archived:
            sql += " AND COALESCE(e.lifecycle, 'active') != 'archived'"

        if kb_name:
            sql += " AND e.kb_name = :kb_name"
            params["kb_name"] = kb_name
        if entry_type:
            sql += " AND e.entry_type = :entry_type"
            params["entry_type"] = entry_type
        if date_from:
            sql += " AND e.date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            sql += " AND e.date <= :date_to"
            params["date_to"] = date_to
        if tags:
            tag_params = {}
            for i, t in enumerate(tags):
                tag_params[f"tag_{i}"] = t
            tag_placeholders = ", ".join(f":tag_{i}" for i in range(len(tags)))
            sql += f"""
                AND e.id IN (
                    SELECT et.entry_id FROM entry_tag et
                    JOIN tag t ON et.tag_id = t.id
                    WHERE t.name IN ({tag_placeholders})
                    GROUP BY et.entry_id, et.kb_name
                    HAVING COUNT(DISTINCT t.name) = :tag_count
                )
            """
            params.update(tag_params)
            params["tag_count"] = len(tags)

        sql += " ORDER BY rank DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        return self._exec(sql, params)

    def search_by_tag(
        self, tag: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT e.* FROM entry e
            JOIN entry_tag et ON e.id = et.entry_id AND e.kb_name = et.kb_name
            JOIN tag t ON et.tag_id = t.id
            WHERE t.name = :tag
        """
        params: dict[str, Any] = {"tag": tag}
        if kb_name:
            sql += " AND e.kb_name = :kb_name"
            params["kb_name"] = kb_name
        sql += " ORDER BY e.date DESC, e.title LIMIT :limit"
        params["limit"] = limit
        return self._exec(sql, params)

    def search_by_date_range(
        self,
        date_from: str,
        date_to: str,
        kb_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM entry WHERE date >= :date_from AND date <= :date_to"
        params: dict[str, Any] = {"date_from": date_from, "date_to": date_to}
        if kb_name:
            sql += " AND kb_name = :kb_name"
            params["kb_name"] = kb_name
        sql += " ORDER BY date ASC LIMIT :limit"
        params["limit"] = limit
        return self._exec(sql, params)

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT DISTINCT e.* FROM entry e
            JOIN entry_tag et ON e.id = et.entry_id AND e.kb_name = et.kb_name
            JOIN tag t ON et.tag_id = t.id
            WHERE (t.name = :prefix OR t.name LIKE :prefix_like)
        """
        params: dict[str, Any] = {"prefix": prefix, "prefix_like": prefix + "/%"}
        if kb_name:
            sql += " AND e.kb_name = :kb_name"
            params["kb_name"] = kb_name
        sql += " ORDER BY e.date DESC, e.title LIMIT :limit"
        params["limit"] = limit
        return self._exec(sql, params)

    # =====================================================================
    # Semantic search (pgvector embeddings)
    # =====================================================================

    def upsert_embedding(self, entry_id: str, kb_name: str, embedding: list[float]) -> bool:
        # Store embedding directly on the entry row
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        result = self._session.execute(
            text(
                "UPDATE entry SET embedding = CAST(:vec AS vector) "
                "WHERE id = :entry_id AND kb_name = :kb_name"
            ),
            {"vec": vec_str, "entry_id": entry_id, "kb_name": kb_name},
        )
        self._session.commit()
        return result.rowcount > 0

    def search_semantic(
        self,
        embedding: list[float],
        kb_name: str | None = None,
        limit: int = 20,
        max_distance: float = 1.3,
    ) -> list[dict[str, Any]]:
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        sql = """
            SELECT e.*, (e.embedding <=> CAST(:vec AS vector)) as distance
            FROM entry e
            WHERE e.embedding IS NOT NULL
        """
        params: dict[str, Any] = {"vec": vec_str}
        if kb_name:
            sql += " AND e.kb_name = :kb_name"
            params["kb_name"] = kb_name
        sql += " ORDER BY e.embedding <=> CAST(:vec2 AS vector) LIMIT :limit"
        params["vec2"] = vec_str
        params["limit"] = limit

        rows = self._exec(sql, params)
        return [r for r in rows if r.get("distance", 0) <= max_distance]

    def has_embeddings(self) -> bool:
        count = self._exec_scalar("SELECT COUNT(*) FROM entry WHERE embedding IS NOT NULL")
        return (count or 0) > 0

    def embedding_stats(self) -> dict[str, Any]:
        vec_count = self._exec_scalar("SELECT COUNT(*) FROM entry WHERE embedding IS NOT NULL") or 0
        entry_count = self._exec_scalar("SELECT COUNT(*) FROM entry") or 0
        return {
            "available": True,
            "count": vec_count,
            "total_entries": entry_count,
            "coverage": f"{vec_count / entry_count * 100:.1f}%" if entry_count > 0 else "0%",
        }

    def get_embedded_rowids(self) -> set[int]:
        rows = self._exec("SELECT id FROM entry WHERE embedding IS NOT NULL")
        # Return entry IDs as a set (Postgres doesn't use rowids the same way)
        return {hash(r["id"]) for r in rows}

    def get_entries_for_embedding(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT id, kb_name, title, summary, body FROM entry"
        params: dict[str, Any] = {}
        if kb_name:
            sql += " WHERE kb_name = :kb_name"
            params["kb_name"] = kb_name
        rows = self._exec(sql, params)
        # Add a synthetic rowid for protocol compatibility
        for i, r in enumerate(rows):
            r["rowid"] = i
        return rows

    def delete_embedding(self, entry_id: str, kb_name: str) -> None:
        self._session.execute(
            text("UPDATE entry SET embedding = NULL WHERE id = :entry_id AND kb_name = :kb_name"),
            {"entry_id": entry_id, "kb_name": kb_name},
        )
        self._session.commit()
