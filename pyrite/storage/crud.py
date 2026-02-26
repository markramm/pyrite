"""
Entry CRUD operations.

Mixin class for insert, update, delete, and get operations on entries.
Uses ORM session for all writes. FTS5 triggers fire automatically on the
underlying INSERT/UPDATE/DELETE at the SQLite level.
"""

import json
from typing import Any

from sqlalchemy import func

from .models import Entry, EntryRef, EntryTag, Link, Source, Tag


class CRUDMixin:
    """Entry create, read, update, delete operations."""

    def upsert_entry(self, entry_data: dict[str, Any]) -> None:
        """Insert or update an entry. Extension fields go into metadata JSON."""
        entry_id = entry_data.get("id")
        kb_name = entry_data.get("kb_name")

        try:
            self._upsert_entry_main(entry_id, kb_name, entry_data)
            self._sync_tags(entry_id, kb_name, entry_data.get("tags", []))
            self._sync_sources(entry_id, kb_name, entry_data.get("sources", []))
            self._sync_links(entry_id, kb_name, entry_data.get("links", []))
            self._sync_entry_refs(entry_id, kb_name, entry_data)

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _upsert_entry_main(self, entry_id: str, kb_name: str, entry_data: dict[str, Any]) -> None:
        """Insert or update the core entry row using ORM merge."""
        metadata = entry_data.get("metadata", {})
        metadata_json = json.dumps(metadata) if metadata else "{}"

        existing = self.session.get(Entry, (entry_id, kb_name))
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
            # Preserve original created_by, update modified_by
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
            self.session.add(entry)
        # Flush so the row exists for relationship syncs and FTS5 trigger fires
        self.session.flush()

    def _sync_tags(self, entry_id: str, kb_name: str, tags: list[str]) -> None:
        """Replace all tags for an entry using ORM."""
        # Delete existing entry_tag associations
        self.session.query(EntryTag).filter_by(
            entry_id=entry_id, kb_name=kb_name
        ).delete()
        self.session.flush()

        for tag_name in tags:
            if not tag_name:
                continue
            # Get or create tag
            tag = self.session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                self.session.add(tag)
                self.session.flush()

            entry_tag = EntryTag(
                entry_id=entry_id,
                kb_name=kb_name,
                tag_id=tag.id,
            )
            self.session.add(entry_tag)

    def _sync_sources(self, entry_id: str, kb_name: str, sources: list[dict[str, Any]]) -> None:
        """Replace all sources for an entry using ORM."""
        self.session.query(Source).filter_by(
            entry_id=entry_id, kb_name=kb_name
        ).delete()

        for src in sources:
            source = Source(
                entry_id=entry_id,
                kb_name=kb_name,
                title=src.get("title", ""),
                url=src.get("url", ""),
                outlet=src.get("outlet", ""),
                date=src.get("date", ""),
                verified=1 if src.get("verified") else 0,
            )
            self.session.add(source)

    def _sync_links(self, entry_id: str, kb_name: str, links: list[dict[str, Any]]) -> None:
        """Replace all outgoing links for an entry using ORM."""
        self.session.query(Link).filter_by(
            source_id=entry_id, source_kb=kb_name
        ).delete()

        for link in links:
            from ..schema import get_inverse_relation

            relation = link.get("relation", "related_to")
            inverse = get_inverse_relation(relation)
            target_kb = link.get("kb", kb_name)
            link_obj = Link(
                source_id=entry_id,
                source_kb=kb_name,
                target_id=link.get("target"),
                target_kb=target_kb,
                relation=relation,
                inverse_relation=inverse,
                note=link.get("note", ""),
            )
            self.session.add(link_obj)

    def _sync_entry_refs(self, entry_id: str, kb_name: str, entry_data: dict) -> None:
        """Sync object-ref fields into entry_ref table using ORM."""
        self.session.query(EntryRef).filter_by(
            source_id=entry_id, source_kb=kb_name
        ).delete()

        refs = entry_data.get("_refs", [])
        for ref in refs:
            entry_ref = EntryRef(
                source_id=entry_id,
                source_kb=kb_name,
                target_id=ref["target_id"],
                target_kb=ref.get("target_kb", kb_name),
                field_name=ref["field_name"],
                target_type=ref.get("target_type"),
            )
            self.session.add(entry_ref)

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        """Delete an entry. Returns True if deleted."""
        count = self.session.query(Entry).filter_by(
            id=entry_id, kb_name=kb_name
        ).delete()
        self.session.commit()
        return count > 0

    def get_entry(self, entry_id: str, kb_name: str) -> dict[str, Any] | None:
        """Get a single entry with all metadata."""
        entry = self.session.get(Entry, (entry_id, kb_name))
        if not entry:
            return None

        result = self._entry_to_dict(entry)
        result["tags"] = self._get_entry_tags(entry_id, kb_name)
        result["sources"] = self._get_entry_sources(entry_id, kb_name)
        result["links"] = self._get_entry_links(entry_id, kb_name)
        return result

    def _entry_to_dict(self, entry: Entry) -> dict[str, Any]:
        """Convert an Entry ORM object to a dict matching the raw SQL dict(row) format."""
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
        """Get tag names for an entry using ORM."""
        results = (
            self.session.query(Tag.name)
            .join(EntryTag, Tag.id == EntryTag.tag_id)
            .filter(EntryTag.entry_id == entry_id, EntryTag.kb_name == kb_name)
            .all()
        )
        return [r[0] for r in results]

    def _get_entry_sources(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get sources for an entry using ORM."""
        sources = (
            self.session.query(Source)
            .filter_by(entry_id=entry_id, kb_name=kb_name)
            .all()
        )
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
        """Get outgoing links for an entry using ORM."""
        links = (
            self.session.query(Link.target_id, Link.target_kb, Link.relation, Link.note)
            .filter_by(source_id=entry_id, source_kb=kb_name)
            .all()
        )
        return [
            {
                "target_id": l[0],
                "target_kb": l[1],
                "relation": l[2],
                "note": l[3],
            }
            for l in links
        ]

    # Allowed sort columns to prevent SQL injection
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
        """List entries with pagination, optionally filtered by KB, type, and/or tag."""
        query = self.session.query(Entry)

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
        """Count entries, optionally filtered by KB, type, and/or tag."""
        query = self.session.query(func.count(func.distinct(Entry.id)))

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
        """Get distinct entry types, optionally filtered by KB."""
        query = self.session.query(Entry.entry_type).filter(
            Entry.entry_type.isnot(None)
        ).distinct()

        if kb_name:
            query = query.filter(Entry.kb_name == kb_name)

        query = query.order_by(Entry.entry_type)
        return [r[0] for r in query.all()]

    def get_entries_for_indexing(self, kb_name: str) -> list[dict[str, Any]]:
        """Get entry id, file_path, indexed_at for incremental indexing."""
        rows = (
            self.session.query(Entry.id, Entry.file_path, Entry.indexed_at)
            .filter_by(kb_name=kb_name)
            .all()
        )
        return [{"id": r[0], "file_path": r[1], "indexed_at": r[2]} for r in rows]
