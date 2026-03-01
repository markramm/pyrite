"""
PostgresBackend — SearchBackend implementation backed by PostgreSQL + tsvector + pgvector.

Reuses the same SQLAlchemy ORM models as SQLiteBackend. Postgres-specific code:
1. FTS: tsvector column + ts_rank() + plainto_tsquery() (replaces FTS5 MATCH + bm25)
2. Embeddings: pgvector column on entry table + <=> cosine (replaces vec_entry virtual table)
3. Connection: postgresql:// engine URI

All other methods (entry CRUD, tags, links, graph, timeline, refs, blocks, folder queries)
use identical ORM code copied from SQLiteBackend.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from pathlib import PurePath
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Block, Entry, EntryRef, EntryTag, Link, Source, Tag

logger = logging.getLogger(__name__)


class _SafeEncoder(json.JSONEncoder):
    """JSON encoder that serializes date/datetime/Path objects safely."""

    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)


def ensure_schema(engine) -> None:
    """Create pgvector extension, FTS column, embedding column, and indexes.

    Idempotent — safe to call on every startup.
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(
            "ALTER TABLE entry ADD COLUMN IF NOT EXISTS fts_vector tsvector"
        ))
        conn.execute(text(
            "ALTER TABLE entry ADD COLUMN IF NOT EXISTS embedding vector(384)"
        ))
        # GIN index for FTS
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_entry_fts "
            "ON entry USING gin(fts_vector)"
        ))
        # IVFFlat index for vector KNN (requires rows to exist; falls back to seq scan if empty)
        # Use HNSW for small corpora — no training needed
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_entry_embedding "
            "ON entry USING hnsw(embedding vector_cosine_ops)"
        ))
        # Trigger to auto-update fts_vector on INSERT/UPDATE
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION entry_fts_trigger() RETURNS trigger AS $$
            BEGIN
                NEW.fts_vector :=
                    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(NEW.body, '')), 'C');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_entry_fts'
                ) THEN
                    CREATE TRIGGER trg_entry_fts
                    BEFORE INSERT OR UPDATE ON entry
                    FOR EACH ROW EXECUTE FUNCTION entry_fts_trigger();
                END IF;
            END $$;
        """))
        conn.commit()


class PostgresBackend:
    """SearchBackend implementation for PostgreSQL + tsvector + pgvector."""

    def __init__(self, session: Session, engine=None):
        self._session = session
        self._engine = engine
        # For raw SQL queries, use session.execute(text(...))

    def close(self) -> None:
        """No-op — connection lifecycle owned by caller."""

    # =====================================================================
    # Raw SQL helper
    # =====================================================================

    def _exec(self, sql: str, params: dict | None = None):
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
    # Entry CRUD (identical to SQLiteBackend — ORM-based)
    # =====================================================================

    def upsert_entry(self, entry_data: dict[str, Any]) -> None:
        entry_id = entry_data.get("id")
        kb_name = entry_data.get("kb_name")
        try:
            self._upsert_entry_main(entry_id, kb_name, entry_data)
            self._sync_tags(entry_id, kb_name, entry_data.get("tags", []))
            self._sync_sources(entry_id, kb_name, entry_data.get("sources", []))
            self._sync_links(entry_id, kb_name, entry_data.get("links", []))
            self._sync_entry_refs(entry_id, kb_name, entry_data)
            self._sync_blocks(entry_id, kb_name, entry_data)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

    def _upsert_entry_main(self, entry_id: str, kb_name: str, entry_data: dict[str, Any]) -> None:
        metadata = entry_data.get("metadata", {})
        metadata_json = json.dumps(metadata, cls=_SafeEncoder) if metadata is not None else "{}"

        existing = self._session.get(Entry, (entry_id, kb_name))
        if existing:
            existing.entry_type = entry_data.get("entry_type")
            existing.title = entry_data.get("title")
            existing.body = entry_data.get("body")
            existing.summary = entry_data.get("summary")
            existing.file_path = entry_data.get("file_path")
            existing.date = entry_data.get("date")
            existing.importance = entry_data.get("importance")
            existing.status = entry_data.get("status")
            existing.location = entry_data.get("location")
            existing.extra_data = metadata_json
            existing.updated_at = entry_data.get("updated_at")
            existing.indexed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            if entry_data.get("created_by") and not existing.created_by:
                existing.created_by = entry_data.get("created_by")
            if entry_data.get("modified_by"):
                existing.modified_by = entry_data.get("modified_by")
        else:
            entry = Entry(
                id=entry_id,
                kb_name=kb_name,
                entry_type=entry_data.get("entry_type"),
                title=entry_data.get("title"),
                body=entry_data.get("body"),
                summary=entry_data.get("summary"),
                file_path=entry_data.get("file_path"),
                date=entry_data.get("date"),
                importance=entry_data.get("importance"),
                status=entry_data.get("status"),
                location=entry_data.get("location"),
                extra_data=metadata_json,
                created_at=entry_data.get("created_at"),
                updated_at=entry_data.get("updated_at"),
                created_by=entry_data.get("created_by"),
                modified_by=entry_data.get("modified_by"),
            )
            self._session.add(entry)
        self._session.flush()

    def _sync_tags(self, entry_id: str, kb_name: str, tags: list[str]) -> None:
        self._session.query(EntryTag).filter_by(entry_id=entry_id, kb_name=kb_name).delete()
        self._session.flush()
        for tag_name in tags:
            if not tag_name:
                continue
            tag = self._session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                self._session.add(tag)
                self._session.flush()
            self._session.add(EntryTag(entry_id=entry_id, kb_name=kb_name, tag_id=tag.id))

    def _sync_sources(self, entry_id: str, kb_name: str, sources: list[dict[str, Any]]) -> None:
        self._session.query(Source).filter_by(entry_id=entry_id, kb_name=kb_name).delete()
        for src in sources:
            self._session.add(Source(
                entry_id=entry_id,
                kb_name=kb_name,
                title=src.get("title", ""),
                url=src.get("url", ""),
                outlet=src.get("outlet", ""),
                date=src.get("date", ""),
                verified=1 if src.get("verified") else 0,
            ))

    def _sync_links(self, entry_id: str, kb_name: str, links: list[dict[str, Any]]) -> None:
        self._session.query(Link).filter_by(source_id=entry_id, source_kb=kb_name).delete()
        for link in links:
            from ...schema import get_inverse_relation
            relation = link.get("relation", "related_to")
            inverse = get_inverse_relation(relation)
            target_kb = link.get("kb", kb_name)
            self._session.add(Link(
                source_id=entry_id,
                source_kb=kb_name,
                target_id=link.get("target"),
                target_kb=target_kb,
                relation=relation,
                inverse_relation=inverse,
                note=link.get("note", ""),
            ))

    def _sync_entry_refs(self, entry_id: str, kb_name: str, entry_data: dict) -> None:
        self._session.query(EntryRef).filter_by(source_id=entry_id, source_kb=kb_name).delete()
        for ref in entry_data.get("_refs", []):
            self._session.add(EntryRef(
                source_id=entry_id,
                source_kb=kb_name,
                target_id=ref["target_id"],
                target_kb=ref.get("target_kb", kb_name),
                field_name=ref["field_name"],
                target_type=ref.get("target_type"),
            ))

    def _sync_blocks(self, entry_id: str, kb_name: str, entry_data: dict) -> None:
        self._session.query(Block).filter_by(entry_id=entry_id, kb_name=kb_name).delete()
        for blk in entry_data.get("_blocks", []):
            self._session.add(Block(
                entry_id=entry_id,
                kb_name=kb_name,
                block_id=blk["block_id"],
                heading=blk.get("heading"),
                content=blk["content"],
                position=blk["position"],
                block_type=blk["block_type"],
            ))

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        count = self._session.query(Entry).filter_by(id=entry_id, kb_name=kb_name).delete()
        self._session.commit()
        return count > 0

    def get_entry(self, entry_id: str, kb_name: str) -> dict[str, Any] | None:
        entry = self._session.get(Entry, (entry_id, kb_name))
        if not entry:
            return None
        result = self._entry_to_dict(entry)
        result["tags"] = self._get_entry_tags(entry_id, kb_name)
        result["sources"] = self._get_entry_sources(entry_id, kb_name)
        result["links"] = self._get_entry_links(entry_id, kb_name)
        return result

    def _entry_to_dict(self, entry: Entry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "kb_name": entry.kb_name,
            "entry_type": entry.entry_type,
            "title": entry.title,
            "body": entry.body,
            "summary": entry.summary,
            "file_path": entry.file_path,
            "date": entry.date,
            "importance": entry.importance,
            "status": entry.status,
            "location": entry.location,
            "metadata": entry.extra_data,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "indexed_at": entry.indexed_at,
            "created_by": entry.created_by,
            "modified_by": entry.modified_by,
        }

    def _get_entry_tags(self, entry_id: str, kb_name: str) -> list[str]:
        results = (
            self._session.query(Tag.name)
            .join(EntryTag, Tag.id == EntryTag.tag_id)
            .filter(EntryTag.entry_id == entry_id, EntryTag.kb_name == kb_name)
            .all()
        )
        return [r[0] for r in results]

    def _get_entry_sources(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        sources = self._session.query(Source).filter_by(entry_id=entry_id, kb_name=kb_name).all()
        return [
            {
                "id": s.id,
                "entry_id": s.entry_id,
                "kb_name": s.kb_name,
                "title": s.title,
                "url": s.url,
                "outlet": s.outlet,
                "date": s.date,
                "verified": s.verified,
            }
            for s in sources
        ]

    def _get_entry_links(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        links = (
            self._session.query(Link.target_id, Link.target_kb, Link.relation, Link.note)
            .filter_by(source_id=entry_id, source_kb=kb_name)
            .all()
        )
        return [
            {"target_id": l[0], "target_kb": l[1], "relation": l[2], "note": l[3]}
            for l in links
        ]

    _SORT_COLUMNS = {"title", "updated_at", "created_at", "entry_type"}

    def list_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = self._session.query(Entry)
        if tag:
            query = (
                query.join(EntryTag, (Entry.id == EntryTag.entry_id) & (Entry.kb_name == EntryTag.kb_name))
                .join(Tag, EntryTag.tag_id == Tag.id)
                .filter(Tag.name == tag)
            )
        if kb_name:
            query = query.filter(Entry.kb_name == kb_name)
        if entry_type:
            query = query.filter(Entry.entry_type == entry_type)
        query = query.distinct()

        col = sort_by if sort_by in self._SORT_COLUMNS else "updated_at"
        sort_col = getattr(Entry, col)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())
        if col != "updated_at":
            query = query.order_by(Entry.updated_at.desc())

        query = query.limit(limit).offset(offset)
        rows = query.all()
        entries = []
        for entry in rows:
            e = self._entry_to_dict(entry)
            e["tags"] = self._get_entry_tags(entry.id, entry.kb_name)
            entries.append(e)
        return entries

    def count_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        from sqlalchemy import func

        query = self._session.query(func.count(func.distinct(Entry.id)))
        if tag:
            query = (
                query.join(EntryTag, (Entry.id == EntryTag.entry_id) & (Entry.kb_name == EntryTag.kb_name))
                .join(Tag, EntryTag.tag_id == Tag.id)
                .filter(Tag.name == tag)
            )
        if kb_name:
            query = query.filter(Entry.kb_name == kb_name)
        if entry_type:
            query = query.filter(Entry.entry_type == entry_type)
        return query.scalar() or 0

    def get_distinct_types(self, kb_name: str | None = None) -> list[str]:
        query = self._session.query(Entry.entry_type).filter(
            Entry.entry_type.isnot(None)
        ).distinct()
        if kb_name:
            query = query.filter(Entry.kb_name == kb_name)
        query = query.order_by(Entry.entry_type)
        return [r[0] for r in query.all()]

    def get_entries_for_indexing(self, kb_name: str) -> list[dict[str, Any]]:
        rows = (
            self._session.query(Entry.id, Entry.file_path, Entry.indexed_at)
            .filter_by(kb_name=kb_name)
            .all()
        )
        return [{"id": r[0], "file_path": r[1], "indexed_at": r[2]} for r in rows]

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
    ) -> list[dict[str, Any]]:
        # Build the tsquery — plainto_tsquery handles user input safely
        sql = """
            SELECT
                e.id, e.kb_name, e.entry_type, e.title, e.summary,
                e.file_path, e.date, e.importance, e.status, e.location,
                e.metadata, e.created_at, e.updated_at, e.indexed_at,
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

    def upsert_embedding(
        self, entry_id: str, kb_name: str, embedding: list[float]
    ) -> bool:
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
        count = self._exec_scalar(
            "SELECT COUNT(*) FROM entry WHERE embedding IS NOT NULL"
        )
        return (count or 0) > 0

    def embedding_stats(self) -> dict[str, Any]:
        vec_count = self._exec_scalar(
            "SELECT COUNT(*) FROM entry WHERE embedding IS NOT NULL"
        ) or 0
        entry_count = self._exec_scalar("SELECT COUNT(*) FROM entry") or 0
        return {
            "available": True,
            "count": vec_count,
            "total_entries": entry_count,
            "coverage": f"{vec_count / entry_count * 100:.1f}%" if entry_count > 0 else "0%",
        }

    def get_embedded_rowids(self) -> set[int]:
        rows = self._exec(
            "SELECT id FROM entry WHERE embedding IS NOT NULL"
        )
        # Return entry IDs as a set (Postgres doesn't use rowids the same way)
        return {hash(r["id"]) for r in rows}

    def get_entries_for_embedding(
        self, kb_name: str | None = None
    ) -> list[dict[str, Any]]:
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
            text(
                "UPDATE entry SET embedding = NULL "
                "WHERE id = :entry_id AND kb_name = :kb_name"
            ),
            {"entry_id": entry_id, "kb_name": kb_name},
        )
        self._session.commit()

    # =====================================================================
    # Graph queries (links) — identical to SQLiteBackend
    # =====================================================================

    def get_backlinks(
        self,
        entry_id: str,
        kb_name: str,
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT e.id, e.kb_name, e.title, e.entry_type,
                   l.inverse_relation as relation, l.note
            FROM link l
            JOIN entry e ON l.source_id = e.id AND l.source_kb = e.kb_name
            WHERE l.target_id = :entry_id AND l.target_kb = :kb_name
        """
        params: dict[str, Any] = {"entry_id": entry_id, "kb_name": kb_name}
        if limit > 0:
            sql += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
        return self._exec(sql, params)

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        return self._exec(
            """
            SELECT l.target_id as id, l.target_kb as kb_name,
                   e.title, e.entry_type, l.relation, l.note
            FROM link l
            LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
            WHERE l.source_id = :entry_id AND l.source_kb = :kb_name
            """,
            {"entry_id": entry_id, "kb_name": kb_name},
        )

    def get_graph_data(
        self,
        center: str | None = None,
        center_kb: str | None = None,
        kb_name: str | None = None,
        entry_type: str | None = None,
        depth: int = 2,
        limit: int = 500,
    ) -> dict[str, Any]:
        depth = max(1, min(3, depth))
        nodes: dict[tuple[str, str], dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        edge_set: set[tuple[str, str, str, str]] = set()

        if center and center_kb:
            row = self._exec_one(
                "SELECT id, kb_name, title, entry_type FROM entry "
                "WHERE id = :center AND kb_name = :center_kb",
                {"center": center, "center_kb": center_kb},
            )
            if not row:
                return {"nodes": [], "edges": []}
            nodes[(row["id"], row["kb_name"])] = row

            frontier = [(center, center_kb)]
            for _hop in range(depth):
                if not frontier or len(nodes) >= limit:
                    break
                next_frontier: list[tuple[str, str]] = []
                for eid, ekb in frontier:
                    if len(nodes) >= limit:
                        break
                    out_rows = self._exec(
                        """SELECT l.target_id, l.target_kb, l.relation,
                                  e.title, e.entry_type
                           FROM link l
                           LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
                           WHERE l.source_id = :eid AND l.source_kb = :ekb""",
                        {"eid": eid, "ekb": ekb},
                    )
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
                                "source_id": eid, "source_kb": ekb,
                                "target_id": tid, "target_kb": tkb,
                                "relation": r["relation"],
                            })
                        if (tid, tkb) not in nodes:
                            nodes[(tid, tkb)] = {
                                "id": tid, "kb_name": tkb,
                                "title": r["title"] or tid,
                                "entry_type": r["entry_type"] or "unknown",
                            }
                            next_frontier.append((tid, tkb))

                    in_rows = self._exec(
                        """SELECT l.source_id, l.source_kb, l.relation,
                                  e.title, e.entry_type
                           FROM link l
                           JOIN entry e ON l.source_id = e.id AND l.source_kb = e.kb_name
                           WHERE l.target_id = :eid AND l.target_kb = :ekb""",
                        {"eid": eid, "ekb": ekb},
                    )
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
                                "source_id": sid, "source_kb": skb,
                                "target_id": eid, "target_kb": ekb,
                                "relation": r["relation"],
                            })
                        if (sid, skb) not in nodes:
                            nodes[(sid, skb)] = {
                                "id": sid, "kb_name": skb,
                                "title": r["title"] or sid,
                                "entry_type": r["entry_type"] or "unknown",
                            }
                            next_frontier.append((sid, skb))

                frontier = next_frontier
        else:
            sql = """
                SELECT e.id, e.kb_name, e.title, e.entry_type
                FROM entry e
                WHERE e.id IN (SELECT source_id FROM link)
                   OR e.id IN (SELECT target_id FROM link)
            """
            params: dict[str, Any] = {}
            if kb_name:
                sql += " AND e.kb_name = :kb_name"
                params["kb_name"] = kb_name
            if entry_type:
                sql += " AND e.entry_type = :entry_type"
                params["entry_type"] = entry_type
            sql += " LIMIT :limit"
            params["limit"] = limit
            for r in self._exec(sql, params):
                nodes[(r["id"], r["kb_name"])] = r
            if nodes:
                link_rows = self._exec(
                    "SELECT source_id, source_kb, target_id, target_kb, relation FROM link"
                )
                for r in link_rows:
                    src = (r["source_id"], r["source_kb"])
                    tgt = (r["target_id"], r["target_kb"])
                    if src in nodes and tgt in nodes:
                        edges.append(r)

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

    def get_most_linked(
        self, kb_name: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT e.id, e.kb_name, e.title, e.entry_type,
                   COUNT(l.id) as link_count
            FROM entry e
            LEFT JOIN link l ON e.id = l.target_id AND e.kb_name = l.target_kb
        """
        params: dict[str, Any] = {}
        if kb_name:
            sql += " WHERE e.kb_name = :kb_name"
            params["kb_name"] = kb_name
        sql += " GROUP BY e.id, e.kb_name, e.title, e.entry_type ORDER BY link_count DESC LIMIT :limit"
        params["limit"] = limit
        return self._exec(sql, params)

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
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
        params: dict[str, Any] = {}
        if kb_name:
            sql += " AND e.kb_name = :kb_name"
            params["kb_name"] = kb_name
        return self._exec(sql, params)

    # =====================================================================
    # Tags — identical to SQLiteBackend
    # =====================================================================

    def get_all_tags(self, kb_name: str | None = None) -> list[tuple[str, int]]:
        if kb_name:
            rows = self._exec(
                """SELECT t.name, COUNT(*) as count
                   FROM tag t JOIN entry_tag et ON t.id = et.tag_id
                   WHERE et.kb_name = :kb_name
                   GROUP BY t.name ORDER BY count DESC""",
                {"kb_name": kb_name},
            )
        else:
            rows = self._exec("""
                SELECT t.name, COUNT(*) as count
                FROM tag t JOIN entry_tag et ON t.id = et.tag_id
                GROUP BY t.name ORDER BY count DESC
            """)
        return [(r["name"], r["count"]) for r in rows]

    def get_tags_as_dicts(
        self,
        kb_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if kb_name:
            conditions.append("et.kb_name = :kb_name")
            params["kb_name"] = kb_name
        if prefix:
            conditions.append("t.name LIKE :prefix")
            params["prefix"] = f"{prefix}%"
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT t.name, COUNT(*) as count
            FROM tag t JOIN entry_tag et ON t.id = et.tag_id
            {where}
            GROUP BY t.name ORDER BY count DESC
            LIMIT :limit OFFSET :offset
        """
        rows = self._exec(sql, params)
        return [{"name": r["name"], "count": r["count"]} for r in rows]

    # =====================================================================
    # Timeline — identical to SQLiteBackend
    # =====================================================================

    def get_timeline(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        min_importance: int = 1,
        kb_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT id, kb_name, title, date, importance, location, summary
            FROM entry
            WHERE date IS NOT NULL AND importance >= :min_importance
        """
        params: dict[str, Any] = {"min_importance": min_importance}
        if kb_name:
            sql += " AND kb_name = :kb_name"
            params["kb_name"] = kb_name
        if date_from:
            sql += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            sql += " AND date <= :date_to"
            params["date_to"] = date_to
        sql += " ORDER BY date ASC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        return self._exec(sql, params)

    # =====================================================================
    # Object refs — identical to SQLiteBackend
    # =====================================================================

    def get_refs_from(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        return self._exec(
            """SELECT r.target_id as id, r.target_kb as kb_name, r.field_name, r.target_type,
                      e.title, e.entry_type
               FROM entry_ref r
               LEFT JOIN entry e ON r.target_id = e.id AND r.target_kb = e.kb_name
               WHERE r.source_id = :entry_id AND r.source_kb = :kb_name""",
            {"entry_id": entry_id, "kb_name": kb_name},
        )

    def get_refs_to(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        return self._exec(
            """SELECT r.source_id as id, r.source_kb as kb_name, r.field_name, r.target_type,
                      e.title, e.entry_type
               FROM entry_ref r
               JOIN entry e ON r.source_id = e.id AND r.source_kb = e.kb_name
               WHERE r.target_id = :entry_id AND r.target_kb = :kb_name""",
            {"entry_id": entry_id, "kb_name": kb_name},
        )

    # =====================================================================
    # Folder queries — identical to SQLiteBackend
    # =====================================================================

    def list_entries_in_folder(
        self,
        kb_name: str,
        folder_path: str,
        sort_by: str = "title",
        sort_order: str = "asc",
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        allowed_sorts = {"title", "entry_type", "updated_at", "created_at", "date"}
        if sort_by not in allowed_sorts:
            sort_by = "title"
        if sort_order not in ("asc", "desc"):
            sort_order = "asc"
        folder_prefix = folder_path.rstrip("/") + "/"
        sql = f"""
            SELECT * FROM entry
            WHERE kb_name = :kb_name AND file_path LIKE :folder_prefix
              AND entry_type != 'collection'
            ORDER BY {sort_by} {sort_order}
            LIMIT :limit OFFSET :offset
        """
        return self._exec(sql, {
            "kb_name": kb_name,
            "folder_prefix": folder_prefix + "%",
            "limit": limit,
            "offset": offset,
        })

    def count_entries_in_folder(self, kb_name: str, folder_path: str) -> int:
        folder_prefix = folder_path.rstrip("/") + "/"
        return self._exec_scalar(
            """SELECT COUNT(*) FROM entry
               WHERE kb_name = :kb_name AND file_path LIKE :folder_prefix
                 AND entry_type != 'collection'""",
            {"kb_name": kb_name, "folder_prefix": folder_prefix + "%"},
        ) or 0

    # =====================================================================
    # Global counts — identical to SQLiteBackend
    # =====================================================================

    def get_global_counts(self) -> dict[str, int]:
        tag_count = self._exec_scalar("SELECT COUNT(*) FROM tag") or 0
        link_count = self._exec_scalar("SELECT COUNT(*) FROM link") or 0
        return {
            "total_tags": tag_count,
            "total_links": link_count,
        }
