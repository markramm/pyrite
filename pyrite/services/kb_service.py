"""
Knowledge Base Service

Unified KB operations used by API, CLI, and UI layers.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .kb_registry_service import KBRegistryService

from ..config import KBConfig, PyriteConfig
from ..exceptions import (
    EntryNotFoundError,
    KBNotFoundError,
    KBReadOnlyError,
    ValidationError,
)
from ..models import Entry
from ..models.factory import build_entry
from ..plugins.context import PluginContext
from ..storage.database import PyriteDB
from ..storage.document_manager import DocumentManager
from ..storage.index import IndexManager
from ..storage.repository import KBRepository
from ..utils.metadata import parse_metadata
from .export_service import ExportService
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
        registry: KBRegistryService | None = None,
    ):
        self.config = config
        self.db = db
        self._index_mgr = IndexManager(db, config)
        self._doc_mgr = doc_mgr or DocumentManager(db, self._index_mgr)
        self._export_svc = ExportService(config, db)
        self._registry: KBRegistryService | None = registry
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
        """List all knowledge bases with stats. Delegates to registry if available."""
        if self._registry:
            return self._registry.list_kbs()
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
        """Get KB config by name. Falls back to registry for DB-only KBs."""
        cfg = self.config.get_kb(name)
        if cfg:
            return cfg
        if self._registry:
            return self._registry.get_kb_config(name)
        return None

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

        # Validate entry (e.g. events require a date, importance range, etc.)
        errors = entry.validate()
        if errors:
            raise ValidationError("; ".join(errors))

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
                extra = {k: v for k, v in spec.items() if k not in ("entry_type", "title", "body")}

                entry = build_entry(entry_type, entry_id=entry_id, title=title, body=body, **extra)
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
                    entry.entry_type,
                    meta,
                    context={"kb_name": kb_name, "kb_type": kb_config.kb_type},
                )
            except Exception as e:
                validation_result["warnings"].append(f"Schema validation skipped: {e}")

        if validate_only:
            return entry, validation_result

        if validation_result.get("errors"):
            raise ValidationError(f"Validation errors: {validation_result['errors']}")

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

    def get_entries(self, ids: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Batch-get multiple entries by (entry_id, kb_name) pairs."""
        return self.db.get_entries(ids)

    def list_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        min_importance: int | None = None,
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
            status=status,
            min_importance=min_importance,
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
        metadata = parse_metadata(entry.get("metadata", {}))

        source_type = metadata.get("source_type", "folder")

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
        status: str | None = None,
        min_importance: int | None = None,
    ) -> int:
        """Count entries, optionally filtered."""
        return self.db.count_entries(
            kb_name=kb_name, entry_type=entry_type, tag=tag,
            status=status, min_importance=min_importance,
        )

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
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        """Get timeline events ordered by date."""
        return self.db.get_timeline(
            date_from=date_from,
            date_to=date_to,
            min_importance=min_importance,
            kb_name=kb_name,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )

    def get_tags(
        self,
        kb_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get tags with counts as dicts."""
        return self.db.get_tags_as_dicts(kb_name=kb_name, limit=limit, offset=offset, prefix=prefix)

    def get_most_linked(self, kb_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get most referenced entries."""
        return self.db.get_most_linked(kb_name, limit)

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get entries with no links."""
        return self.db.get_orphans(kb_name)

    def get_tag_tree(self, kb_name: str | None = None) -> list[dict]:
        """Get hierarchical tag tree."""
        return self.db.get_tag_tree(kb_name=kb_name)

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Search entries by tag prefix (includes child tags)."""
        return self.db.search_by_tag_prefix(prefix, kb_name=kb_name, limit=limit)

    def orient(self, kb_name: str, recent_limit: int = 5) -> dict[str, Any]:
        """One-shot KB orientation summary for agents entering a new KB."""
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB '{kb_name}' not found")

        total = self.count_entries(kb_name=kb_name)
        distinct_types = self.get_distinct_types(kb_name=kb_name)

        # Per-type counts
        types = []
        for t in distinct_types:
            count = self.count_entries(kb_name=kb_name, entry_type=t)
            types.append({"type": t, "count": count})
        types.sort(key=lambda x: x["count"], reverse=True)

        # Top tags
        top_tags = self.get_tags(kb_name=kb_name, limit=10)

        # Recent entries (slim)
        recent = self.list_entries(
            kb_name=kb_name,
            sort_by="updated_at",
            sort_order="desc",
            limit=recent_limit,
        )
        recent_slim = [
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "entry_type": e.get("entry_type"),
                "updated_at": e.get("updated_at"),
            }
            for e in recent
        ]

        # Schema info
        schema_info = {}
        if kb_config.kb_schema:
            try:
                schema_info = kb_config.kb_schema.to_agent_schema()
            except Exception:
                logger.warning("Failed schema-to-agent conversion", exc_info=True)

        # Guidelines from config (if available)
        guidelines = getattr(kb_config, "guidelines", None) or {}

        result = {
            "kb": kb_name,
            "description": kb_config.description or "",
            "kb_type": kb_config.kb_type or "default",
            "read_only": kb_config.read_only,
            "guidelines": guidelines,
            "total_entries": total,
            "types": types,
            "top_tags": top_tags,
            "recent": recent_slim,
            "schema": schema_info,
        }

        # Plugin orient supplements
        from ..plugins.registry import get_registry

        supplements = get_registry().get_orient_supplements(kb_name, kb_config.kb_type or "default")
        if supplements:
            result.update(supplements)

        return result

    def generate_readme(self, kb_name: str) -> str:
        """Generate a README.md for a knowledge base."""
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")

        description = kb_config.description or ""
        total = self.count_entries(kb_name=kb_name)
        distinct_types = self.get_distinct_types(kb_name=kb_name)

        # Per-type counts
        type_counts: list[tuple[str, int]] = []
        for t in distinct_types:
            count = self.count_entries(kb_name=kb_name, entry_type=t)
            type_counts.append((t, count))
        type_counts.sort(key=lambda x: x[1], reverse=True)

        # Build markdown
        lines: list[str] = [f"# {kb_name}", ""]
        if description:
            lines += [description, ""]

        # Contents table
        if type_counts:
            lines += ["## Contents", "", "| Type | Count |", "|------|-------|"]
            for t, count in type_counts:
                lines.append(f"| {t} | {count} |")
            lines.append("")

        # Entries grouped by type
        if total > 0:
            lines.append("## Entries")
            lines.append("")
            for entry_type, _ in type_counts:
                entries = self.list_entries(
                    kb_name=kb_name,
                    entry_type=entry_type,
                    sort_by="importance",
                    sort_order="desc",
                    limit=500,
                )
                type_label = entry_type.replace("_", " ").title()
                lines.append(f"### {type_label}")
                lines.append("")
                for e in entries:
                    title = e.get("title", "Untitled")
                    eid = e.get("id", "")
                    imp = e.get("importance")
                    suffix = f" — importance: {imp}" if imp is not None else ""
                    lines.append(f"- **{title}** (`{eid}`){suffix}")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Generated by Pyrite on {datetime.now(UTC).strftime('%Y-%m-%d')}*")
        lines.append("")

        return "\n".join(lines)

    # Settings: use db.get_setting / db.set_setting / db.get_all_settings /
    # db.delete_setting directly — thin wrappers removed in 0.9.

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

    def check_links(
        self,
        kb_name: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Check for broken links, grouped by missing target."""
        return self.wikilinks.check_links(kb_name=kb_name, limit=limit)

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
    # Protocol-level operations
    # =========================================================================

    def claim_entry(
        self,
        entry_id: str,
        kb_name: str,
        assignee: str,
        *,
        from_status: str = "open",
        to_status: str = "claimed",
    ) -> dict[str, Any]:
        """Atomically claim an Assignable + Statusable entry via CAS.

        Uses compare-and-swap on the index to ensure only one agent can claim.
        On success, updates the markdown file to match.

        Returns:
            Dict with claimed=True on success, or error details.
        """
        from sqlalchemy import text

        session = self.db.session

        # CAS: only update if status matches from_status
        status_clause = (
            f"(status = '{from_status}' OR status IS NULL)"
            if from_status == "open"
            else f"status = '{from_status}'"
        )
        result = session.execute(
            text(f"""UPDATE entry
               SET status = :to_status,
                   assignee = :assignee
               WHERE id = :entry_id AND kb_name = :kb_name
               AND {status_clause}"""),
            {
                "assignee": assignee,
                "entry_id": entry_id,
                "kb_name": kb_name,
                "to_status": to_status,
            },
        )
        session.commit()

        if result.rowcount == 0:
            rows = self.db.execute_sql(
                "SELECT status FROM entry WHERE id = :entry_id AND kb_name = :kb_name",
                {"entry_id": entry_id, "kb_name": kb_name},
            )
            if not rows:
                return {
                    "claimed": False,
                    "error": f"Entry '{entry_id}' not found in KB '{kb_name}'",
                }
            current = rows[0].get("status", from_status)
            return {
                "claimed": False,
                "error": f"Entry '{entry_id}' is '{current}', not '{from_status}'",
                "current_status": current,
            }

        # Update the markdown file to match
        try:
            self.update_entry(entry_id, kb_name, status=to_status, assignee=assignee)
        except Exception as e:
            # Rollback index CAS on file error
            logger.warning("File update failed for claim on %s, rolling back: %s", entry_id, e)
            session.execute(
                text(f"""UPDATE entry
                   SET status = '{from_status}',
                       assignee = NULL
                   WHERE id = :entry_id AND kb_name = :kb_name"""),
                {"entry_id": entry_id, "kb_name": kb_name},
            )
            session.commit()
            return {"claimed": False, "error": f"File update failed: {e}"}

        return {
            "claimed": True,
            "task_id": entry_id,
            "assignee": assignee,
            "status": to_status,
        }

    # =========================================================================
    # Hooks
    # =========================================================================

    @staticmethod
    def _run_hooks(hook_name: str, entry: Entry, context: dict) -> Entry:
        """Run core hooks then plugin hooks, scoped by KB type.

        Hook ordering:
        - ``before_save`` / ``before_delete``: Run BEFORE persistence. If any hook
          raises, the operation is aborted — the entry is NOT saved. All exceptions
          propagate to the caller.
        - ``after_save`` / ``after_delete``: Run AFTER persistence. The entry is
          already committed. Exceptions are logged but swallowed — the operation
          is considered successful.
        """
        # Run core hooks first
        for hook_fn in _CORE_HOOKS.get(hook_name, []):
            try:
                result = hook_fn(entry, context)
                if result is not None:
                    entry = result
            except Exception:
                if hook_name.startswith("before_"):
                    raise
                logger.warning("Core hook %s failed", hook_fn.__name__, exc_info=True)

        # Then run plugin hooks
        try:
            from ..plugins import get_registry

            kb_type = context.get("kb_type", "") if context else ""
            return get_registry().run_hooks_for_kb(hook_name, entry, context, kb_type=kb_type)
        except Exception:
            if hook_name.startswith("before_"):
                raise  # before_* hooks abort the operation on ANY exception
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

    def get_pending_changes(self, kb_name: str) -> dict:
        """
        Get uncommitted changes in a KB, presented as entry-level changes.

        Returns dict with:
            changes: list of {change_type, file_path, title, entry_type,
                              entry_id, current_body, previous_body}
            summary: {total, created, modified, deleted}
        """
        from ..services.git_service import GitService

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(kb_name)

        kb_path = kb_config.path
        if not GitService.is_git_repo(kb_path):
            return {"changes": [], "summary": {"total": 0, "created": 0, "modified": 0, "deleted": 0}}

        status = GitService.get_status(kb_path)
        if status["clean"]:
            return {"changes": [], "summary": {"total": 0, "created": 0, "modified": 0, "deleted": 0}}

        changes = []
        counts = {"created": 0, "modified": 0, "deleted": 0}

        # Combine all changed files
        all_files: dict[str, str] = {}  # filename -> change_type
        for f in status.get("untracked", []):
            if f.endswith(".md"):
                all_files[f] = "created"
        for f in status.get("unstaged", []):
            if f.endswith(".md"):
                if not (kb_path / f).exists():
                    all_files[f] = "deleted"
                elif f not in all_files:
                    all_files[f] = "modified"
        for f in status.get("staged", []):
            if f.endswith(".md") and f not in all_files:
                if not (kb_path / f).exists():
                    all_files[f] = "deleted"
                else:
                    all_files[f] = "modified"

        for file_path, change_type in all_files.items():
            entry_info = self._parse_change_entry(kb_path, file_path, change_type)
            changes.append(entry_info)
            counts[change_type] = counts.get(change_type, 0) + 1

        counts["total"] = len(changes)
        return {"changes": changes, "summary": counts}

    def _parse_change_entry(self, kb_path: Path, file_path: str, change_type: str) -> dict:
        """Parse an entry file to extract metadata for a change record."""
        import subprocess

        result = {
            "change_type": change_type,
            "file_path": file_path,
            "title": file_path,
            "entry_type": "unknown",
            "entry_id": None,
            "current_body": None,
            "previous_body": None,
        }

        # Get current content (for created/modified)
        full_path = kb_path / file_path
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
            result["current_body"] = content
            # Parse frontmatter for title/type/id
            meta = self._extract_frontmatter(content)
            if meta:
                result["title"] = meta.get("title", file_path)
                result["entry_type"] = meta.get("type", "unknown")
                result["entry_id"] = meta.get("id")

        # Get previous content (for modified/deleted)
        if change_type in ("modified", "deleted"):
            try:
                proc = subprocess.run(
                    ["git", "show", f"HEAD:{file_path}"],
                    cwd=str(kb_path),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if proc.returncode == 0:
                    result["previous_body"] = proc.stdout
                    if change_type == "deleted":
                        meta = self._extract_frontmatter(proc.stdout)
                        if meta:
                            result["title"] = meta.get("title", file_path)
                            result["entry_type"] = meta.get("type", "unknown")
                            result["entry_id"] = meta.get("id")
            except Exception:
                pass

        return result

    @staticmethod
    def _extract_frontmatter(content: str) -> dict | None:
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return None
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        try:
            from ..utils.yaml import load_yaml

            return load_yaml(parts[1])
        except Exception:
            return None

    def publish_changes(self, kb_name: str, summary: str | None = None) -> dict:
        """
        Commit and push all pending changes in a KB.

        Auto-generates a commit message from the change summary.
        Returns dict with success, commit_hash, entries_published.
        """
        from ..services.git_service import GitService

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(kb_name)

        kb_path = kb_config.path
        if not GitService.is_git_repo(kb_path):
            return {"success": False, "error": "Not a git repository"}

        # Check what's pending
        pending = self.get_pending_changes(kb_name)
        if pending["summary"]["total"] == 0:
            return {"success": True, "entries_published": 0, "commit_hash": None, "message": "Nothing to publish"}

        # Build commit message
        if summary:
            message = summary
        else:
            parts = []
            s = pending["summary"]
            if s["created"]:
                parts.append(f"Created {s['created']} entr{'y' if s['created'] == 1 else 'ies'}")
            if s["modified"]:
                parts.append(f"Updated {s['modified']} entr{'y' if s['modified'] == 1 else 'ies'}")
            if s["deleted"]:
                parts.append(f"Removed {s['deleted']} entr{'y' if s['deleted'] == 1 else 'ies'}")
            message = "Published: " + ", ".join(parts)

        # Commit
        commit_result = self._export_svc.commit_kb(kb_name, message)
        if not commit_result.get("success"):
            return {"success": False, "error": commit_result.get("error", "Commit failed")}

        # Try to push (non-fatal if no remote)
        push_error = None
        try:
            push_result = self._export_svc.push_kb(kb_name)
            if not push_result.get("success"):
                push_error = push_result.get("message", "Push failed")
        except Exception:
            push_error = "No remote configured"

        return {
            "success": True,
            "commit_hash": commit_result.get("commit_hash"),
            "entries_published": pending["summary"]["total"],
            "message": message,
            "push_error": push_error,
        }


# =============================================================================
# Core hooks — platform-level lifecycle hooks (run before plugin hooks)
# =============================================================================


def _task_validate_transition(entry: Any, context: dict) -> Any:
    """Validate task status transitions against workflow on update."""
    if context.get("operation") != "update":
        return entry
    if not hasattr(entry, "entry_type") or entry.entry_type != "task":
        return entry

    old_status = context.get("old_status")
    new_status = getattr(entry, "status", None)
    if not old_status or not new_status or old_status == new_status:
        return entry

    from ..models.task import TASK_WORKFLOW, can_transition

    if not can_transition(TASK_WORKFLOW, old_status, new_status, "write"):
        raise ValueError(f"Invalid task transition: {old_status} → {new_status}")

    return entry


def _parent_rollup(entry: Any, context: dict) -> Any:
    """Auto-complete parent when all Parentable children reach terminal status."""
    if not hasattr(entry, "entry_type"):
        return entry
    if getattr(entry, "status", "") != "done":
        return entry

    parent_id = getattr(entry, "parent", "")
    if not parent_id:
        return entry

    kb_name = context.get("kb_name", "")
    if not kb_name:
        return entry

    try:
        config = context.get("config")
        db = context.get("db")
        if not config or not db:
            return entry

        from .task_service import TaskService

        svc = TaskService(config, db)
        svc.rollup_parent(parent_id, kb_name)
    except Exception as e:
        logger.warning("Parent rollup failed for %s: %s", parent_id, e)

    return entry


_CORE_HOOKS: dict[str, list] = {
    "before_save": [_task_validate_transition],
    "after_save": [_parent_rollup],
}
