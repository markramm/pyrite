"""
Entry CRUD operations.

Mixin class for insert, update, delete, and get operations on entries.
Delegates to the SearchBackend instance at ``self._backend``.
"""

from typing import Any


class CRUDMixin:
    """Entry create, read, update, delete operations — delegates to backend."""

    def upsert_entry(self, entry_data: dict[str, Any]) -> None:
        """Insert or update an entry. Extension fields go into metadata JSON."""
        self._backend.upsert_entry(entry_data)

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        """Delete an entry. Returns True if deleted."""
        return self._backend.delete_entry(entry_id, kb_name)

    def get_entry(self, entry_id: str, kb_name: str) -> dict[str, Any] | None:
        """Get a single entry with all metadata."""
        return self._backend.get_entry(entry_id, kb_name)

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
        return self._backend.list_entries(
            kb_name=kb_name,
            entry_type=entry_type,
            tag=tag,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    def count_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        """Count entries, optionally filtered by KB, type, and/or tag."""
        return self._backend.count_entries(
            kb_name=kb_name, entry_type=entry_type, tag=tag
        )

    def get_distinct_types(self, kb_name: str | None = None) -> list[str]:
        """Get distinct entry types, optionally filtered by KB."""
        return self._backend.get_distinct_types(kb_name)

    def get_entries_for_indexing(self, kb_name: str) -> list[dict[str, Any]]:
        """Get entry id, file_path, indexed_at for incremental indexing."""
        return self._backend.get_entries_for_indexing(kb_name)
