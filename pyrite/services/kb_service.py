"""
Knowledge Base Service

Unified KB operations used by API, CLI, and UI layers.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from ..config import KBConfig, PyriteConfig
from ..exceptions import (
    EntryNotFoundError,
    KBNotFoundError,
    KBReadOnlyError,
    PyriteError,
    ValidationError,
)
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
        self._embedding_svc = None
        self._embedding_checked = False
        self._embedding_worker = None  # Set externally to enable queue-based embedding

    def _get_embedding_svc(self):
        """Lazy-load embedding service if available."""
        if self._embedding_checked:
            return self._embedding_svc
        self._embedding_checked = True
        try:
            from .embedding_service import EmbeddingService, is_available

            if is_available() and self.db.vec_available:
                self._embedding_svc = EmbeddingService(
                    self.db, model_name=self.config.settings.embedding_model
                )
        except Exception:
            pass
        return self._embedding_svc

    def _auto_embed(self, entry_id: str, kb_name: str) -> None:
        """Embed an entry — via background queue if worker is set, else synchronously."""
        if self._embedding_worker is not None:
            self._embedding_worker.enqueue(entry_id, kb_name)
            return
        svc = self._get_embedding_svc()
        if svc:
            try:
                svc.embed_entry(entry_id, kb_name)
            except Exception as e:
                logger.debug("Auto-embed failed for %s: %s", entry_id, e)

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

        # Auto-embed for semantic search
        self._auto_embed(entry.id, kb_name)

        # Run after_save hooks
        self._run_hooks("after_save", entry, hook_ctx)

        return entry

    def add_entry_from_file(
        self, kb_name: str, source_path: "Path", *, validate_only: bool = False
    ) -> tuple[Entry, dict[str, Any]]:
        """
        Add a markdown file with frontmatter to a knowledge base.

        Reads the file, parses frontmatter, validates, and saves to the KB.
        Frontmatter must include 'type' and 'title'.

        Args:
            kb_name: Target KB name
            source_path: Path to the markdown file
            validate_only: If True, validate without saving

        Returns:
            Tuple of (Entry, validation_result dict with errors/warnings)

        Raises:
            KBNotFoundError: If KB not found
            KBReadOnlyError: If KB is read-only
            ValidationError: If frontmatter is missing required fields or has errors
        """
        from pathlib import Path

        from ..models.core_types import entry_from_frontmatter
        from ..schema import generate_entry_id
        from ..utils.yaml import load_yaml

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")
        if not validate_only and kb_config.read_only:
            raise KBReadOnlyError(f"KB is read-only: {kb_name}")

        source_path = Path(source_path)

        # Read and parse frontmatter
        text = source_path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise ValidationError("File must start with YAML frontmatter (---)")

        end = text.find("---", 3)
        if end < 0:
            raise ValidationError("Could not find closing frontmatter delimiter (---)")

        meta = load_yaml(text[3:end])
        if not meta or not isinstance(meta, dict):
            raise ValidationError("Frontmatter is empty or invalid")

        body = text[end + 3 :].strip()

        # Require type and title
        if "type" not in meta:
            raise ValidationError("Frontmatter must include 'type'")
        if "title" not in meta:
            raise ValidationError("Frontmatter must include 'title'")

        # Generate ID from title if not present
        if "id" not in meta:
            meta["id"] = generate_entry_id(meta["title"])

        # Build Entry object
        entry = entry_from_frontmatter(meta, body)

        # Schema validation if kb.yaml exists
        validation_result: dict[str, Any] = {"errors": [], "warnings": []}
        kb_yaml = kb_config.path / "kb.yaml"
        if kb_yaml.exists():
            try:
                from ..schema import KBSchema

                schema = KBSchema.from_yaml(kb_yaml)
                validation_result = schema.validate_entry(
                    entry.entry_type, meta, context={"kb_name": kb_name}
                )
            except Exception as e:
                validation_result["warnings"].append(f"Schema validation skipped: {e}")

        if validate_only:
            return entry, validation_result

        if validation_result.get("errors"):
            raise ValidationError(
                f"Validation errors: {validation_result['errors']}"
            )

        repo = KBRepository(kb_config)

        # Check for ID collision
        if repo.exists(entry.id):
            raise ValidationError(f"Entry with ID '{entry.id}' already exists in KB '{kb_name}'")

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

        # Auto-embed for semantic search
        self._auto_embed(entry.id, kb_name)

        # Run after_save hooks
        self._run_hooks("after_save", entry, hook_ctx)

        return entry, validation_result

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

        # Auto-embed for semantic search
        self._auto_embed(entry.id, kb_name)

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

    def add_link(
        self,
        source_id: str,
        source_kb: str,
        target_id: str,
        relation: str = "related_to",
        target_kb: str | None = None,
        note: str = "",
    ) -> None:
        """
        Add a link from one entry to another.

        Updates the source entry's frontmatter and re-indexes.

        Args:
            source_id: Source entry ID
            source_kb: Source KB name
            target_id: Target entry ID
            relation: Relationship type (default: related_to)
            target_kb: Target KB (defaults to source_kb)
            note: Optional note about the link
        """
        kb_config = self.config.get_kb(source_kb)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {source_kb}")
        if kb_config.read_only:
            raise KBReadOnlyError(f"KB is read-only: {source_kb}")

        repo = KBRepository(kb_config)
        entry = repo.load(source_id)
        if not entry:
            raise EntryNotFoundError(f"Entry not found: {source_id}")

        tkb = target_kb or source_kb
        # Check for duplicate
        for existing in entry.links:
            if existing.target == target_id and (existing.kb or source_kb) == tkb:
                return  # Link already exists

        entry.add_link(target=target_id, relation=relation, note=note, kb=tkb)
        entry.updated_at = datetime.now(UTC)
        file_path = repo.save(entry)
        self._index_mgr.index_entry(entry, source_kb, file_path)

    # =========================================================================
    # Query Operations (read-only, delegate to db)
    # =========================================================================

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
        """List entries with pagination."""
        return self.db.list_entries(
            kb_name=kb_name,
            entry_type=entry_type,
            tag=tag,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )

    def list_collections(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """List all collection entries."""
        return self.list_entries(kb_name=kb_name, entry_type="collection")

    def get_collection_entries(
        self,
        collection_id: str,
        kb_name: str,
        sort_by: str = "title",
        sort_order: str = "asc",
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get entries belonging to a collection (folder-based or query-based).

        Returns:
            Tuple of (entries, total_count)

        Raises:
            EntryNotFoundError: If collection not found
        """
        entry = self.get_entry(collection_id, kb_name)
        if not entry or entry.get("entry_type") != "collection":
            raise EntryNotFoundError(f"Collection not found: {collection_id}")
        metadata = entry.get("metadata", {})
        if isinstance(metadata, str):
            import json

            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        source_type = metadata.get("source_type", "folder") if isinstance(metadata, dict) else "folder"

        # Virtual collection (query-based)
        if source_type == "query":
            return self._get_query_collection_entries(
                metadata, kb_name, sort_by, sort_order, limit, offset
            )

        # Folder-based collection (Phase 1)
        folder_path = metadata.get("folder_path", "") if isinstance(metadata, dict) else ""
        if not folder_path:
            return [], 0
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")
        abs_folder = str(kb_config.path / folder_path)
        entries = self.db.list_entries_in_folder(
            kb_name, abs_folder, sort_by, sort_order, limit, offset
        )
        total = self.db.count_entries_in_folder(kb_name, abs_folder)
        return entries, total

    def _get_query_collection_entries(
        self,
        metadata: dict,
        kb_name: str,
        sort_by: str,
        sort_order: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Evaluate a query-based virtual collection."""
        from .collection_query import (
            evaluate_query_cached,
            parse_query,
            query_from_dict,
        )

        query_str = metadata.get("query", "")
        entry_filter = metadata.get("entry_filter", {})

        if query_str:
            query = parse_query(query_str)
        elif entry_filter and isinstance(entry_filter, dict):
            query = query_from_dict(entry_filter)
        else:
            return [], 0

        # Override sort/pagination from caller
        query.sort_by = sort_by
        query.sort_order = sort_order
        query.limit = limit
        query.offset = offset

        # Default kb_name if not set in query
        if not query.kb_name:
            query.kb_name = kb_name

        return evaluate_query_cached(query, self.db)

    def count_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        """Count entries, optionally filtered."""
        return self.db.count_entries(kb_name=kb_name, entry_type=entry_type, tag=tag)

    def get_distinct_types(self, kb_name: str | None = None) -> list[str]:
        """Get distinct entry types from the database."""
        return self.db.get_distinct_types(kb_name=kb_name)

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
    # Graph
    # =========================================================================

    def get_graph(
        self,
        center: str | None = None,
        center_kb: str | None = None,
        kb_name: str | None = None,
        entry_type: str | None = None,
        depth: int = 2,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Get graph data for visualization."""
        return self.db.get_graph_data(
            center=center,
            center_kb=center_kb,
            kb_name=kb_name,
            entry_type=entry_type,
            depth=depth,
            limit=limit,
        )

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

    def get_wanted_pages(
        self, kb_name: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get link targets that don't exist as entries (wanted pages)."""
        sql = """
            SELECT l.target_id, l.target_kb, COUNT(*) as ref_count,
                   GROUP_CONCAT(DISTINCT l.source_id) as referenced_by
            FROM link l
            LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
            WHERE e.id IS NULL
        """
        params: list[Any] = []
        if kb_name:
            sql += " AND l.target_kb = ?"
            params.append(kb_name)
        sql += " GROUP BY l.target_id, l.target_kb ORDER BY ref_count DESC LIMIT ?"
        params.append(limit)
        rows = self.db._raw_conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

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

    # =========================================================================
    # Git operations
    # =========================================================================

    def commit_kb(
        self,
        kb_name: str,
        message: str,
        paths: list[str] | None = None,
        sign_off: bool = False,
    ) -> dict:
        """
        Commit changes in a KB's git repository.

        Args:
            kb_name: Knowledge base name
            message: Commit message
            paths: Specific file paths to stage (all changes if None)
            sign_off: Add Signed-off-by line

        Returns:
            dict with success, commit_hash, files_changed, etc.

        Raises:
            KBNotFoundError: KB doesn't exist
            PyriteError: KB is not in a git repository
        """
        from .git_service import GitService

        kb = self.config.get_kb(kb_name)
        if not kb:
            raise KBNotFoundError(f"KB '{kb_name}' not found")

        if not GitService.is_git_repo(kb.path):
            raise PyriteError(f"KB '{kb_name}' is not in a git repository")

        success, result = GitService.commit(
            kb.path, message, paths=paths, sign_off=sign_off
        )

        if success:
            return {"success": True, **result}
        return {"success": False, "error": result.get("error", "Unknown error")}

    def push_kb(
        self,
        kb_name: str,
        remote: str = "origin",
        branch: str | None = None,
    ) -> dict:
        """
        Push KB commits to a remote repository.

        Args:
            kb_name: Knowledge base name
            remote: Remote name (default: origin)
            branch: Branch to push (default: current branch)

        Returns:
            dict with success and message

        Raises:
            KBNotFoundError: KB doesn't exist
            PyriteError: KB is not in a git repository
        """
        from .git_service import GitService

        kb = self.config.get_kb(kb_name)
        if not kb:
            raise KBNotFoundError(f"KB '{kb_name}' not found")

        if not GitService.is_git_repo(kb.path):
            raise PyriteError(f"KB '{kb_name}' is not in a git repository")

        success, msg = GitService.push(kb.path, remote=remote, branch=branch)
        return {"success": success, "message": msg}
