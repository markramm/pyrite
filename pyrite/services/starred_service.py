"""
Starred Entries Service

Business logic for starring, unstarring, listing, and reordering
bookmarked entries. Keeps ORM queries out of the endpoint layer.
"""

from datetime import UTC, datetime

from sqlalchemy import func

from ..storage.database import PyriteDB
from ..storage.models import StarredEntry
from .kb_service import KBService


class StarredService:
    """Service for managing starred/bookmarked entries."""

    def __init__(self, db: PyriteDB, kb_service: KBService):
        self.db = db
        self.kb_service = kb_service

    def list_starred(self, kb: str | None = None) -> list[dict]:
        """List starred entries, optionally filtered by KB.

        Returns a list of dicts with keys: entry_id, kb_name, title,
        sort_order, created_at.  Titles are resolved from the storage
        backend; missing titles degrade gracefully to None.
        """
        query = self.db.session.query(StarredEntry)
        if kb:
            query = query.filter(StarredEntry.kb_name == kb)
        query = query.order_by(StarredEntry.sort_order, StarredEntry.created_at.desc())
        results = query.all()

        # Batch-resolve titles from the storage backend
        title_map = self._resolve_titles(results)

        return [
            {
                "entry_id": r.entry_id,
                "kb_name": r.kb_name,
                "title": title_map.get(f"{r.entry_id}:{r.kb_name}"),
                "sort_order": r.sort_order,
                "created_at": r.created_at,
            }
            for r in results
        ]

    def star_entry(self, entry_id: str, kb_name: str) -> dict:
        """Star/bookmark an entry. Idempotent -- starring an already-starred
        entry returns success without modification.

        Returns a dict with keys: starred, entry_id, kb_name.
        """
        existing = (
            self.db.session.query(StarredEntry)
            .filter(
                StarredEntry.entry_id == entry_id,
                StarredEntry.kb_name == kb_name,
            )
            .first()
        )
        if existing:
            return {"starred": True, "entry_id": entry_id, "kb_name": kb_name}

        max_order = self.db.session.query(func.max(StarredEntry.sort_order)).scalar() or 0

        starred = StarredEntry(
            entry_id=entry_id,
            kb_name=kb_name,
            sort_order=max_order + 1,
            created_at=datetime.now(UTC).isoformat(),
        )
        self.db.session.add(starred)
        self.db.session.commit()

        return {"starred": True, "entry_id": entry_id, "kb_name": kb_name}

    def unstar_entry(self, entry_id: str, kb_name: str | None = None) -> bool:
        """Remove a starred entry.

        Returns True if the entry was found and deleted.
        Raises ValueError if no matching starred entry exists.
        """
        query = self.db.session.query(StarredEntry).filter(
            StarredEntry.entry_id == entry_id
        )
        if kb_name:
            query = query.filter(StarredEntry.kb_name == kb_name)

        deleted_count = query.delete()
        self.db.session.commit()

        if deleted_count == 0:
            raise ValueError(f"Starred entry '{entry_id}' not found")

        return True

    def reorder_starred(self, entries: list[dict]) -> list[dict]:
        """Update sort_order for a batch of starred entries.

        Each dict in *entries* must have keys: entry_id, kb_name, sort_order.
        Returns the same list after persisting the new order.
        """
        for item in entries:
            self.db.session.query(StarredEntry).filter(
                StarredEntry.entry_id == item["entry_id"],
                StarredEntry.kb_name == item["kb_name"],
            ).update({"sort_order": item["sort_order"]})
        self.db.session.commit()

        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_titles(self, results: list) -> dict[str, str]:
        """Batch-resolve entry titles from the storage backend.

        Returns a mapping of ``"entry_id:kb_name"`` to title string.
        Failures are silently ignored so callers degrade gracefully.
        """
        ids_to_fetch = [(r.entry_id, r.kb_name) for r in results]
        title_map: dict[str, str] = {}
        if ids_to_fetch:
            try:
                entries = self.kb_service.get_entries(ids_to_fetch)
                for e in entries:
                    key = f"{e['id']}:{e.get('kb_name', '')}"
                    title_map[key] = e.get("title", "")
            except Exception:
                pass  # Graceful degradation -- titles will be None
        return title_map
