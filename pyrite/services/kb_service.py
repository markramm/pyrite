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
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="create",
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
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="update",
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
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="delete",
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

    def get_tag_tree(self, kb_name: str | None = None) -> list[dict]:
        """Get hierarchical tag tree."""
        return self.db.get_tag_tree(kb_name=kb_name)

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Search entries by tag prefix (includes child tags)."""
        return self.db.search_by_tag_prefix(prefix, kb_name=kb_name, limit=limit)

    # =========================================================================
    # Object References
    # =========================================================================

    def get_refs_to(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that reference this entry via object-ref fields."""
        return self.db.get_refs_to(entry_id, kb_name)

    def get_refs_from(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries this entry references via object-ref fields."""
        return self.db.get_refs_from(entry_id, kb_name)

    # =========================================================================
    # Settings
    # =========================================================================

    def get_setting(self, key: str) -> str | None:
        """Get a setting value by key."""
        return self.db.get_setting(key)

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value (upsert)."""
        self.db.set_setting(key, value)

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings as a dict."""
        return self.db.get_all_settings()

    def delete_setting(self, key: str) -> bool:
        """Delete a setting. Returns True if deleted."""
        return self.db.delete_setting(key)

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
        """Resolve a wikilink target to an entry. Supports kb:id format for cross-KB links."""
        # Parse cross-KB format
        actual_target = target
        actual_kb = kb_name
        if ":" in target and not target.startswith("http"):
            prefix, rest = target.split(":", 1)
            # Look up KB by shortname
            kb_by_short = self.config.get_kb_by_shortname(prefix)
            if kb_by_short:
                actual_target = rest
                actual_kb = kb_by_short.name
            elif self.config.get_kb(prefix):
                actual_target = rest
                actual_kb = prefix

        sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE id = ?"
        params: list[str] = [actual_target]
        if actual_kb:
            sql += " AND kb_name = ?"
            params.append(actual_kb)
        sql += " LIMIT 1"

        row = self.db._raw_conn.execute(sql, params).fetchone()

        if not row:
            sql = "SELECT id, kb_name, entry_type, title FROM entry WHERE title LIKE ?"
            params = [actual_target]
            if actual_kb:
                sql += " AND kb_name = ?"
                params.append(actual_kb)
            sql += " LIMIT 1"
            row = self.db._raw_conn.execute(sql, params).fetchone()

        return dict(row) if row else None

    def resolve_batch(self, targets: list[str], kb_name: str | None = None) -> dict[str, bool]:
        """Batch-resolve wikilink targets. Supports kb:id format."""
        if not targets:
            return {}
        result: dict[str, bool] = {}

        # Separate cross-KB targets from same-KB targets
        simple_targets = []
        for t in targets:
            if ":" in t and not t.startswith("http"):
                # Resolve cross-KB targets individually
                resolved = self.resolve_entry(t, kb_name)
                result[t] = resolved is not None
            else:
                simple_targets.append(t)

        if simple_targets:
            placeholders = ",".join(["?"] * len(simple_targets))
            sql = f"SELECT id FROM entry WHERE id IN ({placeholders})"
            params: list[str] = list(simple_targets)
            if kb_name:
                sql += " AND kb_name = ?"
                params.append(kb_name)
            rows = self.db._raw_conn.execute(sql, params).fetchall()
            existing_ids = {r["id"] for r in rows}
            for t in simple_targets:
                result[t] = t in existing_ids

        return result

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
    # Version History
    # =========================================================================

    def get_entry_versions(self, entry_id: str, kb_name: str, limit: int = 50) -> list[dict]:
        """Get version history for an entry."""
        return self.db.get_entry_versions(entry_id, kb_name, limit=limit)

    def get_entry_at_version(self, entry_id: str, kb_name: str, commit_hash: str) -> str | None:
        """Get entry content at a specific git commit."""
        import subprocess
        from pathlib import Path

        from ..services.git_service import GitService

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return None

        kb_path = kb_config.path
        if not GitService.is_git_repo(kb_path):
            return None

        # Find the file path for this entry
        entry = self.db.get_entry(entry_id, kb_name)
        if not entry or not entry.get("file_path"):
            return None

        file_path = entry["file_path"]
        # Make relative to KB path
        try:
            rel_path = str(Path(file_path).relative_to(kb_path))
        except ValueError:
            rel_path = file_path

        # Use git show to get content at commit
        try:
            result = subprocess.run(
                ["git", "show", f"{commit_hash}:{rel_path}"],
                cwd=str(kb_path),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout
        except Exception:
            pass
        return None

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

    # =========================================================================
    # Ephemeral KBs
    # =========================================================================

    def create_ephemeral_kb(self, name: str, ttl: int = 3600, description: str = "") -> KBConfig:
        """Create an ephemeral KB with TTL."""
        import time

        from ..config import save_config

        # Create temp directory for ephemeral KB
        ephemeral_dir = self.config.settings.workspace_path / "ephemeral" / name
        ephemeral_dir.mkdir(parents=True, exist_ok=True)

        kb = KBConfig(
            name=name,
            path=ephemeral_dir,
            kb_type="generic",
            description=description or f"Ephemeral KB (TTL: {ttl}s)",
            ephemeral=True,
            ttl=ttl,
            created_at_ts=time.time(),
        )
        self.config.add_kb(kb)
        save_config(self.config)

        # Register in DB
        self.db.register_kb(
            name=name,
            kb_type="generic",
            path=str(ephemeral_dir),
            description=kb.description,
        )

        return kb

    def gc_ephemeral_kbs(self) -> list[str]:
        """Garbage-collect expired ephemeral KBs. Returns list of removed KB names."""
        import shutil
        import time

        from ..config import save_config

        removed = []
        now = time.time()

        for kb in list(self.config.knowledge_bases):
            if not kb.ephemeral or not kb.ttl or not kb.created_at_ts:
                continue
            if now - kb.created_at_ts > kb.ttl:
                # Remove from index
                self.db.unregister_kb(kb.name)
                # Remove files
                if kb.path.exists():
                    shutil.rmtree(kb.path, ignore_errors=True)
                # Remove from config
                self.config.remove_kb(kb.name)
                removed.append(kb.name)

        if removed:
            save_config(self.config)

        return removed
