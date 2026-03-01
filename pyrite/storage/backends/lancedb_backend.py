"""
LanceDBBackend — SearchBackend implementation backed by LanceDB.

Key simplifications over SQLiteBackend:
- Embeddings are a column in the entries table (no rowid coupling)
- Built-in FTS via Lance's native index (no FTS5 triggers)
- Native hybrid search in single query (no Python RRF)
- Tags denormalized as array column (no junction table)
- Links, sources, refs, blocks stored in separate LanceDB tables
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path, PurePath
from typing import Any

logger = logging.getLogger(__name__)

# Embedding dimension for all-MiniLM-L6-v2
_EMBED_DIM = 384


class _SafeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)


def _ensure_str(v) -> str:
    """Coerce value to string, None→empty string."""
    if v is None:
        return ""
    return str(v)


class LanceDBBackend:
    """SearchBackend implementation for LanceDB."""

    def __init__(self, db_path: str | Path):
        import lancedb
        import pyarrow as pa

        self._pa = pa
        self._db = lancedb.connect(str(db_path))
        self.vec_available = True  # LanceDB always supports vectors

        # Define schemas
        self._entries_schema = pa.schema([
            pa.field("id", pa.utf8()),
            pa.field("kb_name", pa.utf8()),
            pa.field("entry_type", pa.utf8()),
            pa.field("title", pa.utf8()),
            pa.field("body", pa.utf8()),
            pa.field("summary", pa.utf8()),
            pa.field("file_path", pa.utf8()),
            pa.field("date", pa.utf8()),
            pa.field("importance", pa.int32()),
            pa.field("status", pa.utf8()),
            pa.field("location", pa.utf8()),
            pa.field("metadata", pa.utf8()),  # JSON string
            pa.field("created_at", pa.utf8()),
            pa.field("updated_at", pa.utf8()),
            pa.field("indexed_at", pa.utf8()),
            pa.field("created_by", pa.utf8()),
            pa.field("modified_by", pa.utf8()),
            pa.field("tags", pa.list_(pa.utf8())),
            pa.field("_fts_text", pa.utf8()),  # Combined text for FTS
            pa.field("embedding", pa.list_(pa.float32(), _EMBED_DIM)),
        ])

        self._links_schema = pa.schema([
            pa.field("source_id", pa.utf8()),
            pa.field("source_kb", pa.utf8()),
            pa.field("target_id", pa.utf8()),
            pa.field("target_kb", pa.utf8()),
            pa.field("relation", pa.utf8()),
            pa.field("inverse_relation", pa.utf8()),
            pa.field("note", pa.utf8()),
        ])

        self._sources_schema = pa.schema([
            pa.field("entry_id", pa.utf8()),
            pa.field("kb_name", pa.utf8()),
            pa.field("title", pa.utf8()),
            pa.field("url", pa.utf8()),
            pa.field("outlet", pa.utf8()),
            pa.field("date", pa.utf8()),
            pa.field("verified", pa.int32()),
        ])

        self._refs_schema = pa.schema([
            pa.field("source_id", pa.utf8()),
            pa.field("source_kb", pa.utf8()),
            pa.field("target_id", pa.utf8()),
            pa.field("target_kb", pa.utf8()),
            pa.field("field_name", pa.utf8()),
            pa.field("target_type", pa.utf8()),
        ])

        self._blocks_schema = pa.schema([
            pa.field("entry_id", pa.utf8()),
            pa.field("kb_name", pa.utf8()),
            pa.field("block_id", pa.utf8()),
            pa.field("heading", pa.utf8()),
            pa.field("content", pa.utf8()),
            pa.field("position", pa.int32()),
            pa.field("block_type", pa.utf8()),
        ])

        self._ensure_tables()

    def _ensure_tables(self):
        """Create tables if they don't exist."""
        names = self._db.list_tables()
        if "entries" not in names:
            self._db.create_table("entries", schema=self._entries_schema)
        if "links" not in names:
            self._db.create_table("links", schema=self._links_schema)
        if "sources" not in names:
            self._db.create_table("sources", schema=self._sources_schema)
        if "refs" not in names:
            self._db.create_table("refs", schema=self._refs_schema)
        if "blocks" not in names:
            self._db.create_table("blocks", schema=self._blocks_schema)
        self._entries = self._db.open_table("entries")
        self._links = self._db.open_table("links")
        self._sources = self._db.open_table("sources")
        self._refs = self._db.open_table("refs")
        self._blocks = self._db.open_table("blocks")
        self._fts_dirty = True  # Track whether FTS index needs rebuild

    def _rebuild_fts_if_needed(self):
        """Rebuild FTS index if data has changed."""
        if self._fts_dirty and self._entries.count_rows() > 0:
            try:
                self._entries.create_fts_index("_fts_text", replace=True)
                self._fts_dirty = False
            except Exception as e:
                logger.debug("FTS index rebuild failed: %s", e)

    def close(self) -> None:
        """Release resources."""
        pass  # LanceDB handles cleanup

    # =====================================================================
    # Helpers
    # =====================================================================

    @staticmethod
    def _build_fts_text(entry_data: dict) -> str:
        """Combine title + summary + body for FTS indexing."""
        parts = []
        for field in ("title", "summary", "body"):
            v = entry_data.get(field)
            if v:
                parts.append(str(v))
        return " ".join(parts)

    def _entry_row(self, entry_data: dict) -> dict:
        """Convert entry_data dict to a LanceDB row."""
        metadata = entry_data.get("metadata", {})
        if metadata and not isinstance(metadata, str):
            metadata = json.dumps(metadata, cls=_SafeEncoder)
        elif not metadata:
            metadata = "{}"

        importance = entry_data.get("importance")
        if importance is not None:
            importance = int(importance)
        else:
            importance = 0

        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        tags = entry_data.get("tags", [])
        tags = [t for t in tags if t]  # Filter empty tags

        return {
            "id": _ensure_str(entry_data.get("id")),
            "kb_name": _ensure_str(entry_data.get("kb_name")),
            "entry_type": _ensure_str(entry_data.get("entry_type")),
            "title": _ensure_str(entry_data.get("title")),
            "body": _ensure_str(entry_data.get("body")),
            "summary": _ensure_str(entry_data.get("summary")),
            "file_path": _ensure_str(entry_data.get("file_path")),
            "date": _ensure_str(entry_data.get("date")),
            "importance": importance,
            "status": _ensure_str(entry_data.get("status")),
            "location": _ensure_str(entry_data.get("location")),
            "metadata": metadata,
            "created_at": _ensure_str(entry_data.get("created_at")),
            "updated_at": _ensure_str(entry_data.get("updated_at")),
            "indexed_at": now,
            "created_by": _ensure_str(entry_data.get("created_by")),
            "modified_by": _ensure_str(entry_data.get("modified_by")),
            "tags": tags,
            "_fts_text": self._build_fts_text(entry_data),
            "embedding": [0.0] * _EMBED_DIM,  # Placeholder, updated via upsert_embedding
        }

    def _row_to_entry(self, row: dict) -> dict:
        """Convert a LanceDB row to the standard entry dict format."""
        return {
            "id": row.get("id", ""),
            "kb_name": row.get("kb_name", ""),
            "entry_type": row.get("entry_type", "") or None,
            "title": row.get("title", "") or None,
            "body": row.get("body", "") or None,
            "summary": row.get("summary", "") or None,
            "file_path": row.get("file_path", "") or None,
            "date": row.get("date", "") or None,
            "importance": row.get("importance"),
            "status": row.get("status", "") or None,
            "location": row.get("location", "") or None,
            "metadata": row.get("metadata", "{}"),
            "created_at": row.get("created_at", "") or None,
            "updated_at": row.get("updated_at", "") or None,
            "indexed_at": row.get("indexed_at", "") or None,
            "created_by": row.get("created_by", "") or None,
            "modified_by": row.get("modified_by", "") or None,
        }

    def _escape_str(self, s: str) -> str:
        """Escape a string for LanceDB SQL filter expressions."""
        return s.replace("'", "''")

    # =====================================================================
    # Entry CRUD
    # =====================================================================

    def upsert_entry(self, entry_data: dict[str, Any]) -> None:
        entry_id = entry_data.get("id")
        kb_name = entry_data.get("kb_name")

        # Check if entry exists to preserve embedding
        existing_embedding = None
        existing = self._get_raw_entry(entry_id, kb_name)
        if existing:
            existing_embedding = existing.get("embedding")
            # Preserve created_by
            if entry_data.get("created_by") and not existing.get("created_by"):
                pass  # new created_by takes effect
            elif existing.get("created_by"):
                entry_data.setdefault("created_by", existing.get("created_by"))

        row = self._entry_row(entry_data)
        if existing_embedding is not None:
            # Preserve existing embedding if we had one
            row["embedding"] = existing_embedding

        # Upsert entry
        self._entries.merge_insert(["id", "kb_name"]) \
            .when_matched_update_all() \
            .when_not_matched_insert_all() \
            .execute([row])

        # Sync related data
        self._sync_sources(entry_id, kb_name, entry_data.get("sources", []))
        self._sync_links(entry_id, kb_name, entry_data.get("links", []))
        self._sync_refs(entry_id, kb_name, entry_data)
        self._sync_blocks(entry_id, kb_name, entry_data)
        self._fts_dirty = True

    def _get_raw_entry(self, entry_id: str, kb_name: str) -> dict | None:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        rows = self._entries.search().where(
            f"id = '{eid}' AND kb_name = '{kb}'"
        ).limit(1).to_list()
        return rows[0] if rows else None

    def _sync_sources(self, entry_id: str, kb_name: str, sources: list[dict]) -> None:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            self._sources.delete(f"entry_id = '{eid}' AND kb_name = '{kb}'")
        except Exception:
            pass
        if sources:
            rows = [{
                "entry_id": entry_id,
                "kb_name": kb_name,
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "outlet": s.get("outlet", ""),
                "date": s.get("date", ""),
                "verified": 1 if s.get("verified") else 0,
            } for s in sources]
            self._sources.add(rows)

    def _sync_links(self, entry_id: str, kb_name: str, links: list[dict]) -> None:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            self._links.delete(f"source_id = '{eid}' AND source_kb = '{kb}'")
        except Exception:
            pass
        if links:
            from ...schema import get_inverse_relation
            rows = []
            for link in links:
                relation = link.get("relation", "related_to")
                inverse = get_inverse_relation(relation)
                target_kb = link.get("kb", kb_name)
                rows.append({
                    "source_id": entry_id,
                    "source_kb": kb_name,
                    "target_id": link.get("target", ""),
                    "target_kb": target_kb,
                    "relation": relation,
                    "inverse_relation": inverse,
                    "note": link.get("note", ""),
                })
            self._links.add(rows)

    def _sync_refs(self, entry_id: str, kb_name: str, entry_data: dict) -> None:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            self._refs.delete(f"source_id = '{eid}' AND source_kb = '{kb}'")
        except Exception:
            pass
        refs = entry_data.get("_refs", [])
        if refs:
            rows = [{
                "source_id": entry_id,
                "source_kb": kb_name,
                "target_id": ref["target_id"],
                "target_kb": ref.get("target_kb", kb_name),
                "field_name": ref["field_name"],
                "target_type": ref.get("target_type", ""),
            } for ref in refs]
            self._refs.add(rows)

    def _sync_blocks(self, entry_id: str, kb_name: str, entry_data: dict) -> None:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            self._blocks.delete(f"entry_id = '{eid}' AND kb_name = '{kb}'")
        except Exception:
            pass
        blocks = entry_data.get("_blocks", [])
        if blocks:
            rows = [{
                "entry_id": entry_id,
                "kb_name": kb_name,
                "block_id": blk["block_id"],
                "heading": blk.get("heading", ""),
                "content": blk["content"],
                "position": blk["position"],
                "block_type": blk["block_type"],
            } for blk in blocks]
            self._blocks.add(rows)

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        before = self._entries.count_rows(f"id = '{eid}' AND kb_name = '{kb}'")
        if before == 0:
            return False
        self._entries.delete(f"id = '{eid}' AND kb_name = '{kb}'")
        # Cascade deletes
        try:
            self._links.delete(f"source_id = '{eid}' AND source_kb = '{kb}'")
        except Exception:
            pass
        try:
            self._sources.delete(f"entry_id = '{eid}' AND kb_name = '{kb}'")
        except Exception:
            pass
        try:
            self._refs.delete(f"source_id = '{eid}' AND source_kb = '{kb}'")
        except Exception:
            pass
        try:
            self._blocks.delete(f"entry_id = '{eid}' AND kb_name = '{kb}'")
        except Exception:
            pass
        self._fts_dirty = True
        return True

    def get_entry(self, entry_id: str, kb_name: str) -> dict[str, Any] | None:
        raw = self._get_raw_entry(entry_id, kb_name)
        if not raw:
            return None
        result = self._row_to_entry(raw)
        result["tags"] = raw.get("tags", [])
        result["sources"] = self._get_entry_sources(entry_id, kb_name)
        result["links"] = self._get_entry_links(entry_id, kb_name)
        return result

    def _get_entry_sources(self, entry_id: str, kb_name: str) -> list[dict]:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            rows = self._sources.search().where(
                f"entry_id = '{eid}' AND kb_name = '{kb}'"
            ).limit(1000).to_list()
        except Exception:
            return []
        return [{
            "id": i,
            "entry_id": r.get("entry_id", ""),
            "kb_name": r.get("kb_name", ""),
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "outlet": r.get("outlet", ""),
            "date": r.get("date", ""),
            "verified": r.get("verified", 0),
        } for i, r in enumerate(rows)]

    def _get_entry_links(self, entry_id: str, kb_name: str) -> list[dict]:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            rows = self._links.search().where(
                f"source_id = '{eid}' AND source_kb = '{kb}'"
            ).limit(1000).to_list()
        except Exception:
            return []
        return [{
            "target_id": r.get("target_id", ""),
            "target_kb": r.get("target_kb", ""),
            "relation": r.get("relation", ""),
            "note": r.get("note", ""),
        } for r in rows]

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
        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        if entry_type:
            conditions.append(f"entry_type = '{self._escape_str(entry_type)}'")
        if tag:
            conditions.append(f"list_contains(tags, '{self._escape_str(tag)}')")

        where = " AND ".join(conditions) if conditions else None

        query = self._entries.search()
        if where:
            query = query.where(where)

        # LanceDB doesn't support offset natively on search(), so fetch more
        rows = query.limit(limit + offset).to_list()

        # Manual sort
        allowed_sorts = {"title", "updated_at", "created_at", "entry_type"}
        col = sort_by if sort_by in allowed_sorts else "updated_at"
        reverse = sort_order.lower() != "asc"
        rows.sort(key=lambda r: r.get(col) or "", reverse=reverse)

        # Apply offset
        rows = rows[offset:offset + limit]

        entries = []
        for r in rows:
            e = self._row_to_entry(r)
            e["tags"] = r.get("tags", [])
            entries.append(e)
        return entries

    def count_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        if entry_type:
            conditions.append(f"entry_type = '{self._escape_str(entry_type)}'")

        where = " AND ".join(conditions) if conditions else None

        if tag:
            # count_rows doesn't support list_contains, need to fetch
            tag_cond = f"list_contains(tags, '{self._escape_str(tag)}')"
            full_where = f"{where} AND {tag_cond}" if where else tag_cond
            rows = self._entries.search().where(full_where).limit(100000).to_list()
            return len(rows)

        return self._entries.count_rows(where)

    def get_distinct_types(self, kb_name: str | None = None) -> list[str]:
        where = f"kb_name = '{self._escape_str(kb_name)}'" if kb_name else None
        if where:
            rows = self._entries.search().where(where).limit(100000).to_list()
        else:
            rows = self._entries.search().limit(100000).to_list()
        types = sorted({r["entry_type"] for r in rows if r.get("entry_type")})
        return types

    def get_entries_for_indexing(self, kb_name: str) -> list[dict[str, Any]]:
        kb = self._escape_str(kb_name)
        rows = self._entries.search().where(f"kb_name = '{kb}'").limit(100000).to_list()
        return [{"id": r["id"], "file_path": r.get("file_path"), "indexed_at": r.get("indexed_at")} for r in rows]

    # =====================================================================
    # Full-text search
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
        self._rebuild_fts_if_needed()

        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        if entry_type:
            conditions.append(f"entry_type = '{self._escape_str(entry_type)}'")
        if date_from:
            conditions.append(f"date >= '{self._escape_str(date_from)}'")
        if date_to:
            conditions.append(f"date <= '{self._escape_str(date_to)}'")
        if tags:
            for tag in tags:
                conditions.append(f"list_contains(tags, '{self._escape_str(tag)}')")

        try:
            q = self._entries.search(query, query_type="fts")
            if conditions:
                q = q.where(" AND ".join(conditions))
            rows = q.limit(limit + offset).to_list()
        except Exception:
            # FTS index may not exist yet or query syntax issue
            return []

        rows = rows[offset:offset + limit]

        results = []
        for r in rows:
            entry = self._row_to_entry(r)
            entry["tags"] = r.get("tags", [])
            entry["snippet"] = r.get("_fts_text", "")[:200]
            entry["rank"] = r.get("_score", 0)
            results.append(entry)
        return results

    def search_by_tag(
        self, tag: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        conditions = [f"list_contains(tags, '{self._escape_str(tag)}')"]
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        where = " AND ".join(conditions)
        rows = self._entries.search().where(where).limit(limit).to_list()
        rows.sort(key=lambda r: (r.get("date") or "", r.get("title") or ""), reverse=True)
        return [self._row_to_entry(r) for r in rows]

    def search_by_date_range(
        self,
        date_from: str,
        date_to: str,
        kb_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        conditions = [
            f"date >= '{self._escape_str(date_from)}'",
            f"date <= '{self._escape_str(date_to)}'",
        ]
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        where = " AND ".join(conditions)
        rows = self._entries.search().where(where).limit(limit).to_list()
        rows.sort(key=lambda r: r.get("date") or "")
        return [self._row_to_entry(r) for r in rows]

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        # LanceDB doesn't have native tag prefix search, fetch and filter
        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        where = " AND ".join(conditions) if conditions else None
        if where:
            rows = self._entries.search().where(where).limit(100000).to_list()
        else:
            rows = self._entries.search().limit(100000).to_list()

        results = []
        for r in rows:
            tags = r.get("tags", [])
            if any(t == prefix or t.startswith(prefix + "/") for t in tags):
                results.append(self._row_to_entry(r))
                if len(results) >= limit:
                    break
        results.sort(key=lambda r: (r.get("date") or "", r.get("title") or ""), reverse=True)
        return results

    # =====================================================================
    # Semantic search (embeddings)
    # =====================================================================

    def upsert_embedding(
        self, entry_id: str, kb_name: str, embedding: list[float]
    ) -> bool:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            self._entries.update(
                where=f"id = '{eid}' AND kb_name = '{kb}'",
                values={"embedding": embedding},
            )
            return True
        except Exception as e:
            logger.warning("Failed to upsert embedding for %s: %s", entry_id, e)
            return False

    def search_semantic(
        self,
        embedding: list[float],
        kb_name: str | None = None,
        limit: int = 20,
        max_distance: float = 1.3,
    ) -> list[dict[str, Any]]:
        fetch_limit = limit * 3 if kb_name else limit * 2
        q = self._entries.search(embedding)
        if kb_name:
            q = q.where(f"kb_name = '{self._escape_str(kb_name)}'")
        rows = q.limit(fetch_limit).to_list()

        results = []
        for r in rows:
            distance = r.get("_distance", 0)
            if distance > max_distance:
                continue
            entry = self._row_to_entry(r)
            entry["distance"] = distance
            entry["tags"] = r.get("tags", [])
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def has_embeddings(self) -> bool:
        # Check if any entry has a non-zero embedding
        rows = self._entries.search().limit(1).to_list()
        if not rows:
            return False
        emb = rows[0].get("embedding", [])
        return any(v != 0.0 for v in emb)

    def embedding_stats(self) -> dict[str, Any]:
        total = self._entries.count_rows()
        if total == 0:
            return {"available": True, "count": 0, "total_entries": 0, "coverage": "0%"}
        # Count entries with non-zero embeddings (sample-based)
        rows = self._entries.search().limit(100000).to_list()
        count = sum(1 for r in rows if any(v != 0.0 for v in (r.get("embedding") or [])))
        return {
            "available": True,
            "count": count,
            "total_entries": total,
            "coverage": f"{count / total * 100:.1f}%" if total > 0 else "0%",
        }

    def get_embedded_rowids(self) -> set[int]:
        # LanceDB doesn't use rowids like SQLite. Return empty set.
        # The embedding check is done differently for LanceDB.
        return set()

    def get_entries_for_embedding(
        self, kb_name: str | None = None
    ) -> list[dict[str, Any]]:
        if kb_name:
            kb = self._escape_str(kb_name)
            rows = self._entries.search().where(f"kb_name = '{kb}'").limit(100000).to_list()
        else:
            rows = self._entries.search().limit(100000).to_list()
        return [{"rowid": i, "id": r["id"], "kb_name": r["kb_name"],
                 "title": r.get("title", ""), "summary": r.get("summary", ""),
                 "body": r.get("body", "")} for i, r in enumerate(rows)]

    def delete_embedding(self, entry_id: str, kb_name: str) -> None:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            self._entries.update(
                where=f"id = '{eid}' AND kb_name = '{kb}'",
                values={"embedding": [0.0] * _EMBED_DIM},
            )
        except Exception:
            pass

    # =====================================================================
    # Graph (links)
    # =====================================================================

    def get_backlinks(
        self,
        entry_id: str,
        kb_name: str,
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            link_rows = self._links.search().where(
                f"target_id = '{eid}' AND target_kb = '{kb}'"
            ).limit(10000).to_list()
        except Exception:
            return []

        results = []
        for lr in link_rows:
            sid = lr["source_id"]
            skb = lr["source_kb"]
            entry = self._get_raw_entry(sid, skb)
            results.append({
                "id": sid,
                "kb_name": skb,
                "title": entry.get("title", "") if entry else sid,
                "entry_type": entry.get("entry_type", "") if entry else "",
                "relation": lr.get("inverse_relation", ""),
                "note": lr.get("note", ""),
            })

        if limit > 0:
            results = results[offset:offset + limit]
        return results

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            link_rows = self._links.search().where(
                f"source_id = '{eid}' AND source_kb = '{kb}'"
            ).limit(10000).to_list()
        except Exception:
            return []

        results = []
        for lr in link_rows:
            tid = lr["target_id"]
            tkb = lr["target_kb"]
            entry = self._get_raw_entry(tid, tkb)
            results.append({
                "id": tid,
                "kb_name": tkb,
                "title": entry.get("title", "") if entry else None,
                "entry_type": entry.get("entry_type", "") if entry else None,
                "relation": lr.get("relation", ""),
                "note": lr.get("note", ""),
            })
        return results

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
        nodes: dict[tuple[str, str], dict] = {}
        edges: list[dict] = []
        edge_set: set[tuple[str, str, str, str]] = set()

        if center and center_kb:
            raw = self._get_raw_entry(center, center_kb)
            if not raw:
                return {"nodes": [], "edges": []}
            nodes[(center, center_kb)] = {
                "id": center, "kb_name": center_kb,
                "title": raw.get("title", center),
                "entry_type": raw.get("entry_type", "unknown"),
            }

            frontier = [(center, center_kb)]
            for _hop in range(depth):
                if not frontier or len(nodes) >= limit:
                    break
                next_frontier = []
                for eid, ekb in frontier:
                    if len(nodes) >= limit:
                        break
                    # Outgoing
                    for ol in self.get_outlinks(eid, ekb):
                        if len(nodes) >= limit:
                            break
                        tid, tkb = ol["id"], ol["kb_name"]
                        if kb_name and tkb != kb_name:
                            continue
                        if entry_type and ol.get("entry_type") and ol["entry_type"] != entry_type:
                            continue
                        ek = (eid, ekb, tid, tkb)
                        if ek not in edge_set:
                            edge_set.add(ek)
                            edges.append({"source_id": eid, "source_kb": ekb,
                                          "target_id": tid, "target_kb": tkb,
                                          "relation": ol.get("relation", "")})
                        if (tid, tkb) not in nodes:
                            nodes[(tid, tkb)] = {
                                "id": tid, "kb_name": tkb,
                                "title": ol.get("title") or tid,
                                "entry_type": ol.get("entry_type") or "unknown",
                            }
                            next_frontier.append((tid, tkb))

                    # Incoming
                    for bl in self.get_backlinks(eid, ekb):
                        if len(nodes) >= limit:
                            break
                        sid, skb = bl["id"], bl["kb_name"]
                        if kb_name and skb != kb_name:
                            continue
                        if entry_type and bl.get("entry_type") and bl["entry_type"] != entry_type:
                            continue
                        ek = (sid, skb, eid, ekb)
                        if ek not in edge_set:
                            edge_set.add(ek)
                            edges.append({"source_id": sid, "source_kb": skb,
                                          "target_id": eid, "target_kb": ekb,
                                          "relation": bl.get("relation", "")})
                        if (sid, skb) not in nodes:
                            nodes[(sid, skb)] = {
                                "id": sid, "kb_name": skb,
                                "title": bl.get("title") or sid,
                                "entry_type": bl.get("entry_type") or "unknown",
                            }
                            next_frontier.append((sid, skb))
                frontier = next_frontier
        else:
            # No center: all linked entries
            try:
                all_links = self._links.search().limit(100000).to_list()
            except Exception:
                all_links = []

            linked_ids = set()
            for lr in all_links:
                linked_ids.add((lr["source_id"], lr["source_kb"]))
                linked_ids.add((lr["target_id"], lr["target_kb"]))

            for eid, ekb in list(linked_ids)[:limit]:
                if kb_name and ekb != kb_name:
                    continue
                raw = self._get_raw_entry(eid, ekb)
                if not raw:
                    continue
                if entry_type and raw.get("entry_type") != entry_type:
                    continue
                nodes[(eid, ekb)] = {
                    "id": eid, "kb_name": ekb,
                    "title": raw.get("title", eid),
                    "entry_type": raw.get("entry_type", "unknown"),
                }

            for lr in all_links:
                src = (lr["source_id"], lr["source_kb"])
                tgt = (lr["target_id"], lr["target_kb"])
                if src in nodes and tgt in nodes:
                    edges.append({
                        "source_id": lr["source_id"], "source_kb": lr["source_kb"],
                        "target_id": lr["target_id"], "target_kb": lr["target_kb"],
                        "relation": lr.get("relation", ""),
                    })

        node_list = []
        for node in nodes.values():
            count = sum(
                1 for e in edges
                if (e["source_id"] == node["id"] and e["source_kb"] == node["kb_name"])
                or (e["target_id"] == node["id"] and e["target_kb"] == node["kb_name"])
            )
            node["link_count"] = count
            node_list.append(node)
        return {"nodes": node_list, "edges": edges}

    def get_most_linked(
        self, kb_name: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        # Count incoming links per entry
        try:
            all_links = self._links.search().limit(100000).to_list()
        except Exception:
            all_links = []

        link_counts: dict[tuple[str, str], int] = {}
        for lr in all_links:
            key = (lr["target_id"], lr["target_kb"])
            link_counts[key] = link_counts.get(key, 0) + 1

        # Get all entries
        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        where = " AND ".join(conditions) if conditions else None
        if where:
            entries = self._entries.search().where(where).limit(100000).to_list()
        else:
            entries = self._entries.search().limit(100000).to_list()

        results = []
        for r in entries:
            key = (r["id"], r["kb_name"])
            results.append({
                "id": r["id"], "kb_name": r["kb_name"],
                "title": r.get("title", ""), "entry_type": r.get("entry_type", ""),
                "link_count": link_counts.get(key, 0),
            })
        results.sort(key=lambda x: x["link_count"], reverse=True)
        return results[:limit]

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        try:
            all_links = self._links.search().limit(100000).to_list()
        except Exception:
            all_links = []

        linked_ids = set()
        for lr in all_links:
            linked_ids.add((lr["source_id"], lr["source_kb"]))
            linked_ids.add((lr["target_id"], lr["target_kb"]))

        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        where = " AND ".join(conditions) if conditions else None
        if where:
            entries = self._entries.search().where(where).limit(100000).to_list()
        else:
            entries = self._entries.search().limit(100000).to_list()

        return [
            {"id": r["id"], "kb_name": r["kb_name"],
             "title": r.get("title", ""), "entry_type": r.get("entry_type", "")}
            for r in entries
            if (r["id"], r["kb_name"]) not in linked_ids
        ]

    # =====================================================================
    # Tags
    # =====================================================================

    def get_all_tags(self, kb_name: str | None = None) -> list[tuple[str, int]]:
        conditions = []
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        where = " AND ".join(conditions) if conditions else None
        if where:
            rows = self._entries.search().where(where).limit(100000).to_list()
        else:
            rows = self._entries.search().limit(100000).to_list()

        tag_counts: dict[str, int] = {}
        for r in rows:
            for tag in (r.get("tags") or []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags

    def get_tags_as_dicts(
        self,
        kb_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        tags = self.get_all_tags(kb_name)
        if prefix:
            tags = [(name, count) for name, count in tags if name.startswith(prefix)]
        tags = tags[offset:offset + limit]
        return [{"name": name, "count": count} for name, count in tags]

    # =====================================================================
    # Timeline
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
        conditions = [f"importance >= {min_importance}", "date != ''"]
        if kb_name:
            conditions.append(f"kb_name = '{self._escape_str(kb_name)}'")
        if date_from:
            conditions.append(f"date >= '{self._escape_str(date_from)}'")
        if date_to:
            conditions.append(f"date <= '{self._escape_str(date_to)}'")

        where = " AND ".join(conditions)
        rows = self._entries.search().where(where).limit(limit + offset).to_list()
        rows.sort(key=lambda r: r.get("date") or "")
        rows = rows[offset:offset + limit]

        return [{
            "id": r["id"], "kb_name": r["kb_name"], "title": r.get("title", ""),
            "date": r.get("date", ""), "importance": r.get("importance"),
            "location": r.get("location", "") or None, "summary": r.get("summary", "") or None,
        } for r in rows]

    # =====================================================================
    # Object refs
    # =====================================================================

    def get_refs_from(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            ref_rows = self._refs.search().where(
                f"source_id = '{eid}' AND source_kb = '{kb}'"
            ).limit(10000).to_list()
        except Exception:
            return []

        results = []
        for rr in ref_rows:
            tid = rr["target_id"]
            tkb = rr["target_kb"]
            entry = self._get_raw_entry(tid, tkb)
            results.append({
                "id": tid, "kb_name": tkb,
                "field_name": rr.get("field_name", ""),
                "target_type": rr.get("target_type", ""),
                "title": entry.get("title", "") if entry else None,
                "entry_type": entry.get("entry_type", "") if entry else None,
            })
        return results

    def get_refs_to(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        eid = self._escape_str(entry_id)
        kb = self._escape_str(kb_name)
        try:
            ref_rows = self._refs.search().where(
                f"target_id = '{eid}' AND target_kb = '{kb}'"
            ).limit(10000).to_list()
        except Exception:
            return []

        results = []
        for rr in ref_rows:
            sid = rr["source_id"]
            skb = rr["source_kb"]
            entry = self._get_raw_entry(sid, skb)
            results.append({
                "id": sid, "kb_name": skb,
                "field_name": rr.get("field_name", ""),
                "target_type": rr.get("target_type", ""),
                "title": entry.get("title", "") if entry else None,
                "entry_type": entry.get("entry_type", "") if entry else None,
            })
        return results

    # =====================================================================
    # Folder queries
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
        folder_prefix = folder_path.rstrip("/") + "/"
        kb = self._escape_str(kb_name)
        fp = self._escape_str(folder_prefix)
        where = f"kb_name = '{kb}' AND starts_with(file_path, '{fp}') AND entry_type != 'collection'"
        try:
            rows = self._entries.search().where(where).limit(limit + offset).to_list()
        except Exception:
            # starts_with may not be available, fall back to fetching all
            rows = self._entries.search().where(
                f"kb_name = '{kb}' AND entry_type != 'collection'"
            ).limit(100000).to_list()
            rows = [r for r in rows if (r.get("file_path") or "").startswith(folder_prefix)]

        allowed_sorts = {"title", "entry_type", "updated_at", "created_at", "date"}
        col = sort_by if sort_by in allowed_sorts else "title"
        reverse = sort_order.lower() != "asc"
        rows.sort(key=lambda r: r.get(col) or "", reverse=reverse)
        rows = rows[offset:offset + limit]
        return [self._row_to_entry(r) for r in rows]

    def count_entries_in_folder(self, kb_name: str, folder_path: str) -> int:
        folder_prefix = folder_path.rstrip("/") + "/"
        kb = self._escape_str(kb_name)
        # Need to fetch and filter since count_rows may not support starts_with
        rows = self._entries.search().where(
            f"kb_name = '{kb}' AND entry_type != 'collection'"
        ).limit(100000).to_list()
        return sum(1 for r in rows if (r.get("file_path") or "").startswith(folder_prefix))

    # =====================================================================
    # Global counts
    # =====================================================================

    def get_global_counts(self) -> dict[str, int]:
        tags = self.get_all_tags()
        try:
            link_count = self._links.count_rows()
        except Exception:
            link_count = 0
        return {
            "total_tags": len(tags),
            "total_links": link_count,
        }
