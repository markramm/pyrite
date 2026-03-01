"""
Knowledge Base Service

Unified KB operations used by API, CLI, and UI layers.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
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
from ..storage.document_manager import DocumentManager
from ..storage.index import IndexManager
from ..storage.repository import KBRepository
from .wikilink_service import WikilinkService

logger = logging.getLogger(__name__)


class KBService:
    """
    Service for KB operations.

    Provides:
    - KB listing and stats
    - Entry CRUD with proper type handling
    - Index synchronization
    """

    def __init__(
        self,
        config: PyriteConfig,
        db: PyriteDB,
        doc_mgr: DocumentManager | None = None,
    ):
        self.config = config
        self.db = db
        self._index_mgr = IndexManager(db, config)
        self._doc_mgr = doc_mgr or DocumentManager(db, self._index_mgr)
        self._embedding_svc = None
        self._embedding_checked = False
        self._embedding_worker = None  # Set externally to enable queue-based embedding
        self._wikilink_svc: WikilinkService | None = None

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
            logger.warning("Embedding service initialization failed", exc_info=True)
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

    @property
    def wikilinks(self) -> WikilinkService:
        """Lazy WikilinkService instance."""
        if self._wikilink_svc is None:
            self._wikilink_svc = WikilinkService(self.config, self.db)
        return self._wikilink_svc

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

    def _resolve_entry_type(self, entry_type: str) -> str:
        """Resolve a generic core type to a plugin subtype if one exists.

        If a plugin provides a type that subclasses the core type for the
        given name, prefer the plugin type.  E.g. "event" -> "timeline_event"
        when the Cascade plugin registers TimelineEventEntry(EventEntry).
        """
        from ..models.core_types import ENTRY_TYPE_REGISTRY

        core_cls = ENTRY_TYPE_REGISTRY.get(entry_type)
        if not core_cls:
            return entry_type
        try:
            from ..plugins import get_registry

            for ptype_name, ptype_cls in get_registry().get_all_entry_types().items():
                if ptype_name != entry_type and issubclass(ptype_cls, core_cls):
                    return ptype_name
        except Exception:
            logger.warning("Plugin type resolution failed for %s", entry_type, exc_info=True)
        return entry_type

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

        # Resolve generic core type to plugin subtype if one exists
        entry_type = self._resolve_entry_type(entry_type)

        # Create appropriate entry type via factory
        entry = build_entry(entry_type, entry_id=entry_id, title=title, body=body, **kwargs)

        # Run before_save hooks
        hook_ctx = PluginContext(
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="create",
            kb_type=kb_config.kb_type,
        )
        entry = self._run_hooks("before_save", entry, hook_ctx)

        # Save to file, register KB, and index
        self._doc_mgr.save_entry(entry, kb_name, kb_config)

        # Auto-embed for semantic search
        self._auto_embed(entry.id, kb_name)

        # Run after_save hooks
        self._run_hooks("after_save", entry, hook_ctx)

        return entry

    def bulk_create_entries(
        self,
        kb_name: str,
        entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Create multiple entries in a single batch.

        Each entry spec should have at least {entry_type, title} plus optional
        fields (body, date, importance, tags, metadata, etc.).

        Returns a list of result dicts, one per input entry:
            {"created": True, "entry_id": "..."} on success
            {"created": False, "error": "..."} on failure
        """
        from ..schema import generate_entry_id

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")
        if kb_config.read_only:
            raise KBReadOnlyError(f"KB is read-only: {kb_name}")

        hook_ctx = PluginContext(
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="create",
            kb_type=kb_config.kb_type,
        )

        results: list[dict[str, Any]] = []
        created_ids: list[tuple[str, str]] = []  # (entry_id, kb_name) for batch embed

        for spec in entries:
            try:
                entry_type = spec.get("entry_type", "note")
                title = spec.get("title")
                if not title:
                    results.append({"created": False, "error": "title is required"})
                    continue

                body = spec.get("body", "")
                entry_id = generate_entry_id(title)

                # Resolve type
                entry_type = self._resolve_entry_type(entry_type)

                # Build extra kwargs
                extra = {
                    k: v
                    for k, v in spec.items()
                    if k not in ("entry_type", "title", "body")
                }

                entry = build_entry(
                    entry_type, entry_id=entry_id, title=title, body=body, **extra
                )
                entry = self._run_hooks("before_save", entry, hook_ctx)

                self._doc_mgr.save_entry(entry, kb_name, kb_config)
                self._run_hooks("after_save", entry, hook_ctx)

                created_ids.append((entry.id, kb_name))
                results.append({"created": True, "entry_id": entry.id})
            except Exception as e:
                results.append({"created": False, "error": str(e)})

        # Batch embed all created entries
        for eid, ekb in created_ids:
            self._auto_embed(eid, ekb)

        return results

    def add_entry_from_file(
        self, kb_name: str, source_path: Path, *, validate_only: bool = False
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
                schema = kb_config.kb_schema
                validation_result = schema.validate_entry(
                    entry.entry_type, meta,
                    context={"kb_name": kb_name, "kb_type": kb_config.kb_type},
                )
            except Exception as e:
                validation_result["warnings"].append(f"Schema validation skipped: {e}")

        if validate_only:
            return entry, validation_result

        if validation_result.get("errors"):
            raise ValidationError(
                f"Validation errors: {validation_result['errors']}"
            )

        # Check for ID collision
        repo = KBRepository(kb_config)
        if repo.exists(entry.id):
            raise ValidationError(f"Entry with ID '{entry.id}' already exists in KB '{kb_name}'")

        # Run before_save hooks
        hook_ctx = PluginContext(
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="create",
            kb_type=kb_config.kb_type,
        )
        entry = self._run_hooks("before_save", entry, hook_ctx)

        # Save to file, register KB, and index
        self._doc_mgr.save_entry(entry, kb_name, kb_config)

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

        # Capture old_status before applying updates (for workflow hooks)
        old_status = getattr(entry, "status", None)

        # Apply updates
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)

        entry.updated_at = datetime.now(UTC)

        # Run before_save hooks
        extra = {"old_status": old_status} if old_status else {}
        hook_ctx = PluginContext(
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="update",
            kb_type=kb_config.kb_type,
            extra=extra,
        )
        entry = self._run_hooks("before_save", entry, hook_ctx)

        # Save to file, register KB, and re-index
        self._doc_mgr.save_entry(entry, kb_name, kb_config)

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

        # Load entry for hooks before deleting
        repo = KBRepository(kb_config)
        entry = repo.load(entry_id)
        hook_ctx = PluginContext(
            config=self.config,
            db=self.db,
            kb_name=kb_name,
            user="",
            operation="delete",
            kb_type=kb_config.kb_type,
        )
        if entry:
            entry = self._run_hooks("before_delete", entry, hook_ctx)

        # Delete from file system and index
        file_deleted = self._doc_mgr.delete_entry(entry_id, kb_name, kb_config)

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
        self._doc_mgr.save_entry(entry, source_kb, kb_config)

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
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get timeline events ordered by date."""
        return self.db.get_timeline(
            date_from=date_from,
            date_to=date_to,
            min_importance=min_importance,
            kb_name=kb_name,
            limit=limit,
            offset=offset,
        )

    def get_tags(
        self,
        kb_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get tags with counts as dicts."""
        return self.db.get_tags_as_dicts(
            kb_name=kb_name, limit=limit, offset=offset, prefix=prefix
        )

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

    # Settings: use db.get_setting / db.set_setting / db.get_all_settings /
    # db.delete_setting directly — thin wrappers removed in 0.9.

    def get_backlinks(
        self,
        entry_id: str,
        kb_name: str,
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get entries that link TO this entry."""
        return self.db.get_backlinks(entry_id, kb_name, limit=limit, offset=offset)

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that this entry links TO."""
        return self.db.get_outlinks(entry_id, kb_name)

    # =========================================================================
    # Wikilink delegation (implementation in WikilinkService)
    # =========================================================================

    def list_entry_titles(
        self,
        kb_name: str | None = None,
        query: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Lightweight listing of entry IDs and titles for wikilink autocomplete."""
        return self.wikilinks.list_entry_titles(kb_name=kb_name, query=query, limit=limit)

    def resolve_entry(self, target: str, kb_name: str | None = None) -> dict[str, Any] | None:
        """Resolve a wikilink target to an entry. Supports kb:id format for cross-KB links."""
        return self.wikilinks.resolve_entry(target, kb_name=kb_name)

    def resolve_batch(self, targets: list[str], kb_name: str | None = None) -> dict[str, bool]:
        """Batch-resolve wikilink targets. Supports kb:id format."""
        return self.wikilinks.resolve_batch(targets, kb_name=kb_name)

    def get_wanted_pages(
        self, kb_name: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get link targets that don't exist as entries (wanted pages)."""
        return self.wikilinks.get_wanted_pages(kb_name=kb_name, limit=limit)

    def list_daily_dates(self, kb_name: str, month: str) -> list[str]:
        """List dates that have daily notes for a given month (YYYY-MM)."""
        prefix = f"daily-{month}"
        sql = "SELECT id FROM entry WHERE kb_name = :kb_name AND id LIKE :prefix ORDER BY id"
        rows = self.db.execute_sql(sql, {"kb_name": kb_name, "prefix": f"{prefix}%"})

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
            self._doc_mgr.index_entry(entry, kb_name, file_path)

    # =========================================================================
    # Version History
    # =========================================================================

    def get_entry_versions(self, entry_id: str, kb_name: str, limit: int = 50) -> list[dict]:
        """Get version history for an entry."""
        return self.db.get_entry_versions(entry_id, kb_name, limit=limit)

    def get_entry_at_version(self, entry_id: str, kb_name: str, commit_hash: str) -> str | None:
        """Get entry content at a specific git commit."""
        import subprocess

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
            logger.warning("Git diff failed for KB", exc_info=True)
        return None

    # =========================================================================
    # Hooks
    # =========================================================================

    @staticmethod
    def _run_hooks(hook_name: str, entry: Entry, context: dict) -> Entry:
        """Run plugin lifecycle hooks, scoped by KB type. Returns the (possibly modified) entry."""
        try:
            from ..plugins import get_registry

            kb_type = context.get("kb_type", "") if context else ""
            return get_registry().run_hooks_for_kb(hook_name, entry, context, kb_type=kb_type)
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
