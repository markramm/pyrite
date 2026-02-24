"""
Knowledge Base Service

Unified KB operations used by API, CLI, and UI layers.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from ..config import KBConfig, PyriteConfig
from ..exceptions import EntryNotFoundError, KBNotFoundError, KBReadOnlyError, PyriteError
from ..models import Entry
from ..models.factory import build_entry
from ..plugins.context import PluginContext
from ..storage.database import PyriteDB
from ..storage.index import IndexManager
from ..storage.repository import KBRepository

logger = logging.getLogger(__name__)


class KBService:
    """
    Service for KB operations.

    Provides:
    - KB listing and stats
    - Entry CRUD with proper type handling
    - Index synchronization
    """

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db
        self._index_mgr = IndexManager(db, config)

    # =========================================================================
    # KB Operations
    # =========================================================================

    def list_kbs(self) -> list[dict[str, Any]]:
        """List all configured knowledge bases with stats."""
        kbs = []
        for kb in self.config.knowledge_bases:
            stats = self.db.get_kb_stats(kb.name)
            kbs.append(
                {
                    "name": kb.name,
                    "type": kb.kb_type,
                    "path": str(kb.path),
                    "description": kb.description,
                    "read_only": kb.read_only,
                    "entries": stats.get("entry_count", 0) if stats else 0,
                    "indexed": bool(stats.get("last_indexed")) if stats else False,
                    "last_indexed": stats.get("last_indexed") if stats else None,
                }
            )
        return kbs

    def get_kb(self, name: str) -> KBConfig | None:
        """Get KB config by name."""
        return self.config.get_kb(name)

    def get_kb_stats(self, name: str) -> dict[str, Any] | None:
        """Get stats for a specific KB."""
        return self.db.get_kb_stats(name)

    # =========================================================================
    # Entry Operations
    # =========================================================================

    def get_entry(self, entry_id: str, kb_name: str | None = None) -> dict[str, Any] | None:
        """
        Get entry by ID.

        If kb_name not specified, searches all KBs.
        """
        if kb_name:
            result = self.db.get_entry(entry_id, kb_name)
            if result:
                result["outlinks"] = self.db.get_outlinks(entry_id, kb_name)
                result["backlinks"] = self.db.get_backlinks(entry_id, kb_name)
            return result

        # Search all KBs
        for kb in self.config.knowledge_bases:
            result = self.db.get_entry(entry_id, kb.name)
            if result:
                result["outlinks"] = self.db.get_outlinks(entry_id, kb.name)
                result["backlinks"] = self.db.get_backlinks(entry_id, kb.name)
                return result
        return None

    def create_entry(
        self, kb_name: str, entry_id: str, title: str, entry_type: str, body: str = "", **kwargs
    ) -> Entry:
        """
        Create a new entry.

        Args:
            kb_name: Target KB name
            entry_id: Entry ID (filename without .md)
            title: Entry title
            entry_type: Type (event, person, organization, note, topic, etc.)
            body: Markdown body content
            **kwargs: Additional fields (date, importance, tags, etc.)

        Returns:
            Created Entry object

        Raises:
            KBNotFoundError: If KB not found
            KBReadOnlyError: If KB is read-only
        """
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")
        if kb_config.read_only:
            raise KBReadOnlyError(f"KB is read-only: {kb_name}")

        repo = KBRepository(kb_config)

        # Create appropriate entry type via factory
        entry = build_entry(entry_type, entry_id=entry_id, title=title, body=body, **kwargs)

        # Run before_save hooks
        hook_ctx = PluginContext(
            config=self.config, db=self.db, kb_name=kb_name, user="", operation="create",
        )
        entry = self._run_hooks("before_save", entry, hook_ctx)

        # Save to file
        file_path = repo.save(entry)

        # Ensure KB is registered before indexing
        self.db.register_kb(
            name=kb_name,
            kb_type=kb_config.kb_type,
            path=str(kb_config.path),
            description=kb_config.description,
        )

        # Index the entry
        self._index_mgr.index_entry(entry, kb_name, file_path)

        # Run after_save hooks
        self._run_hooks("after_save", entry, hook_ctx)

        return entry

    def update_entry(self, entry_id: str, kb_name: str, **updates) -> Entry:
        """
        Update an existing entry.

        Args:
            entry_id: Entry ID to update
            kb_name: KB containing the entry
            **updates: Fields to update

        Returns:
            Updated Entry object

        Raises:
            KBNotFoundError: If KB not found
            KBReadOnlyError: If KB is read-only
            EntryNotFoundError: If entry not found
        """
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")
        if kb_config.read_only:
            raise KBReadOnlyError(f"KB is read-only: {kb_name}")

        repo = KBRepository(kb_config)
        entry = repo.load(entry_id)
        if not entry:
            raise EntryNotFoundError(f"Entry not found: {entry_id}")

        # Apply updates
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.now(UTC)

        # Run before_save hooks
        hook_ctx = PluginContext(
            config=self.config, db=self.db, kb_name=kb_name, user="", operation="update",
        )
        entry = self._run_hooks("before_save", entry, hook_ctx)

        # Save to file
        file_path = repo.save(entry)

        # Re-index
        self._index_mgr.index_entry(entry, kb_name, file_path)

        # Run after_save hooks
        self._run_hooks("after_save", entry, hook_ctx)

        return entry

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        """
        Delete an entry.

        Returns:
            True if deleted, False if not found

        Raises:
            KBNotFoundError: If KB not found
            KBReadOnlyError: If KB is read-only
        """
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")
        if kb_config.read_only:
            raise KBReadOnlyError(f"KB is read-only: {kb_name}")

        repo = KBRepository(kb_config)

        # Load entry for hooks before deleting
        entry = repo.load(entry_id)
        hook_ctx = PluginContext(
            config=self.config, db=self.db, kb_name=kb_name, user="", operation="delete",
        )
        if entry:
            entry = self._run_hooks("before_delete", entry, hook_ctx)

        # Delete from file system
        file_deleted = repo.delete(entry_id)

        # Delete from index
        self.db.delete_entry(entry_id, kb_name)

        # Run after_delete hooks
        if entry:
            self._run_hooks("after_delete", entry, hook_ctx)

        return file_deleted

    # =========================================================================
    # Query Operations (read-only, delegate to db)
    # =========================================================================

    def list_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List entries with pagination."""
        return self.db.list_entries(
            kb_name=kb_name, entry_type=entry_type, limit=limit, offset=offset
        )

    def count_entries(self, kb_name: str | None = None, entry_type: str | None = None) -> int:
        """Count entries, optionally filtered."""
        return self.db.count_entries(kb_name=kb_name, entry_type=entry_type)

    def get_timeline(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        min_importance: int = 1,
        kb_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get timeline events ordered by date."""
        return self.db.get_timeline(
            date_from=date_from,
            date_to=date_to,
            min_importance=min_importance,
            kb_name=kb_name,
        )

    def get_tags(self, kb_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get tags with counts as dicts."""
        return self.db.get_tags_as_dicts(kb_name=kb_name, limit=limit)

    def get_backlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that link TO this entry."""
        return self.db.get_backlinks(entry_id, kb_name)

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that this entry links TO."""
        return self.db.get_outlinks(entry_id, kb_name)

    def list_entry_titles(
        self,
        kb_name: str | None = None,
        query: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Lightweight listing of entry IDs and titles for wikilink autocomplete."""
        sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE 1=1"
        params: list[str | int] = []

        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)
        if query:
            sql += " AND title LIKE ?"
            params.append(f"%{query}%")

        sql += " ORDER BY title COLLATE NOCASE LIMIT ?"
        params.append(limit)

        rows = self.db._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def resolve_entry(self, target: str, kb_name: str | None = None) -> dict[str, Any] | None:
        """Resolve a wikilink target to an entry. Tries exact ID, then title match."""
        sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE id = ?"
        params: list[str] = [target]
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)
        sql += " LIMIT 1"

        row = self.db._raw_conn.execute(sql, params).fetchone()

        if not row:
            sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE title LIKE ?"
            params = [target]
            if kb_name:
                sql += " AND kb_name = ?"
                params.append(kb_name)
            sql += " LIMIT 1"
            row = self.db._raw_conn.execute(sql, params).fetchone()

        return dict(row) if row else None

    def list_daily_dates(self, kb_name: str, month: str) -> list[str]:
        """List dates that have daily notes for a given month (YYYY-MM)."""
        prefix = f"daily-{month}"
        sql = "SELECT id FROM entry WHERE kb_name = ? AND id LIKE ? ORDER BY id"
        rows = self.db._raw_conn.execute(sql, (kb_name, f"{prefix}%")).fetchall()

        dates = []
        for row in rows:
            entry_id = row["id"]
            if entry_id.startswith("daily-") and len(entry_id) >= 16:
                dates.append(entry_id[6:])  # strip "daily-"
        return dates

    def load_entry_from_disk(self, entry_id: str, kb_name: str) -> Entry | None:
        """Load an entry from disk via KBRepository."""
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return None
        repo = KBRepository(kb_config)
        return repo.load(entry_id)

    def index_entry_from_disk(self, entry: Entry, kb_name: str) -> None:
        """Index an entry that was loaded from disk."""
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return
        repo = KBRepository(kb_config)
        file_path = repo.find_file(entry.id)
        if file_path:
            self._index_mgr.index_entry(entry, kb_name, file_path)

    # =========================================================================
    # Hooks
    # =========================================================================

    @staticmethod
    def _run_hooks(hook_name: str, entry: Entry, context: dict) -> Entry:
        """Run plugin lifecycle hooks. Returns the (possibly modified) entry."""
        try:
            from ..plugins import get_registry

            return get_registry().run_hooks(hook_name, entry, context)
        except PyriteError:
            raise  # Let Pyrite exceptions propagate (e.g. hook aborts)
        except Exception:
            logger.warning("Hook %s failed", hook_name, exc_info=True)
            return entry

    # =========================================================================
    # Index Operations
    # =========================================================================

    def sync_index(self, kb_name: str | None = None) -> dict[str, Any]:
        """
        Synchronize index with file system.

        Args:
            kb_name: Specific KB to sync, or None for all

        Returns:
            Sync statistics
        """
        return self._index_mgr.sync_incremental(kb_name)

    def get_index_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return self._index_mgr.get_index_stats()
