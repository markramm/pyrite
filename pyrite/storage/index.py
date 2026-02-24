"""
Index Manager - Syncs File Storage with SQLite Index

Handles indexing entries from file-based KBs into the SQLite FTS database.
Supports incremental updates based on file modification times.
"""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import PyriteConfig, load_config
from ..models import Entry, EventEntry
from .database import PyriteDB
from .repository import KBRepository

logger = logging.getLogger(__name__)

_WIKILINK_RE = re.compile(r"\[\[(?:([a-z0-9-]+):)?([^\]|]+?)(?:\|[^\]]+?)?\]\]")


class IndexManager:
    """
    Manages the SQLite FTS index for all KBs.

    Responsibilities:
    - Full reindexing of KBs
    - Incremental updates based on file changes
    - Index statistics and health checks
    """

    def __init__(self, db: PyriteDB, config: PyriteConfig | None = None):
        self.db = db
        self.config = config or load_config()

    def _entry_to_dict(self, entry: Entry, kb_name: str, file_path: Path) -> dict[str, Any]:
        """Convert an Entry to a dict for database storage."""
        data = {
            "id": entry.id,
            "kb_name": kb_name,
            "entry_type": entry.entry_type,
            "title": entry.title,
            "body": entry.body,
            "summary": entry.summary,
            "file_path": str(file_path),
            "tags": entry.tags,
            "sources": [s.to_dict() for s in entry.sources],
            "links": [l.to_dict() for l in entry.links],
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        }

        # Event-specific fields
        if isinstance(entry, EventEntry):
            data["date"] = entry.date
            data["importance"] = entry.importance
            # Handle status (could be enum, string, or list)
            status = entry.status
            if hasattr(status, "value"):
                status = status.value
            elif isinstance(status, list):
                status = status[0] if status else None
            data["status"] = status
            # Handle location (could be list)
            location = entry.location
            if isinstance(location, list):
                location = ", ".join(str(loc) for loc in location)
            data["location"] = location
            data["actors"] = entry.participants if hasattr(entry, "participants") else []
        else:
            # Core types with importance
            if hasattr(entry, "importance"):
                data["importance"] = entry.importance

        # Store extension-specific fields in metadata column
        # Use to_frontmatter() to capture all fields, then strip keys
        # already stored in their own DB columns

        # Keys that map to actual DB columns (always excluded from metadata)
        db_column_keys = {
            "id",
            "type",
            "title",
            "body",
            "summary",
            "tags",
            "sources",
            "links",
            "provenance",
            "metadata",
            "created_at",
            "updated_at",
        }
        # Also exclude keys that were explicitly set in data above
        stored_keys = db_column_keys | set(data.keys())
        try:
            fm = entry.to_frontmatter()
            ext_fields = {k: v for k, v in fm.items() if k not in stored_keys}
            # Merge in the explicit metadata dict if present
            if hasattr(entry, "metadata") and entry.metadata:
                ext_fields.update(entry.metadata)
            if ext_fields:
                data["metadata"] = ext_fields  # stored as dict; upsert_entry JSON-encodes
        except Exception:
            # Fallback: just store the metadata dict
            if hasattr(entry, "metadata") and entry.metadata:
                data["metadata"] = entry.metadata

        # Extract object-ref fields for entry_ref table
        refs = []
        try:
            from ..schema import KBSchema

            kb_config = self.config.get_kb(kb_name)
            if kb_config and (kb_config.path / "kb.yaml").exists():
                schema = KBSchema.from_yaml(kb_config.path / "kb.yaml")
                entry_type_name = entry.entry_type
                type_schema = schema.types.get(entry_type_name)
                if type_schema:
                    fm = entry.to_frontmatter()
                    for field_name, field_schema in type_schema.fields.items():
                        if field_schema.field_type == "object-ref":
                            value = fm.get(field_name)
                            if value:
                                target_type = field_schema.constraints.get("target_type")
                                if isinstance(value, list):
                                    for v in value:
                                        if isinstance(v, str):
                                            refs.append(
                                                {
                                                    "target_id": v,
                                                    "field_name": field_name,
                                                    "target_type": target_type,
                                                }
                                            )
                                elif isinstance(value, str):
                                    refs.append(
                                        {
                                            "target_id": value,
                                            "field_name": field_name,
                                            "target_type": target_type,
                                        }
                                    )
        except Exception:
            pass  # Schema not available; skip ref extraction
        if refs:
            data["_refs"] = refs

        # Extract body wikilinks as links with relation="wikilink"
        body = entry.body or ""
        if body:
            existing_targets = {l.get("target") for l in data["links"]}
            for match in _WIKILINK_RE.finditer(body):
                kb_prefix = match.group(1)  # Optional kb: prefix
                target = match.group(2).strip()
                if target and target != entry.id and target not in existing_targets:
                    link_data = {
                        "target": target,
                        "kb": kb_prefix or kb_name,
                        "relation": "wikilink",
                        "note": "",
                    }
                    data["links"].append(link_data)
                    existing_targets.add(target)

        return data

    def index_kb(
        self, kb_name: str, progress_callback: Callable[[int, int], None] | None = None
    ) -> int:
        """
        Fully reindex a knowledge base.

        Args:
            kb_name: Name of the KB to index
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            Number of entries indexed
        """
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise ValueError(f"KB '{kb_name}' not found in config")

        repo = KBRepository(kb_config)

        # Register KB in database
        self.db.register_kb(
            name=kb_name,
            kb_type=kb_config.kb_type,
            path=str(kb_config.path),
            description=kb_config.description,
        )

        # Count total files for progress
        total_files = repo.count()
        indexed_count = 0
        error_count = 0

        # Index all entries
        for entry, file_path in repo.list_entries():
            try:
                data = self._entry_to_dict(entry, kb_name, file_path)
                self.db.upsert_entry(data)
                indexed_count += 1

                if progress_callback:
                    progress_callback(indexed_count, total_files)

            except Exception as e:
                logger.error("Failed to index %s: %s", file_path, e)
                error_count += 1

        # Update KB stats
        self.db.update_kb_indexed(kb_name, indexed_count)

        if error_count > 0:
            logger.warning("%d entries failed to index", error_count)

        return indexed_count

    def index_all(
        self, progress_callback: Callable[[str, int, int], None] | None = None
    ) -> dict[str, int]:
        """
        Index all configured KBs.

        Args:
            progress_callback: Optional callback(kb_name, current, total)

        Returns:
            Dict of kb_name -> entries indexed
        """
        results = {}

        for kb in self.config.knowledge_bases:
            if not kb.path.exists():
                logger.warning("Skipping %s: path does not exist", kb.name)
                continue

            def make_kb_progress(kb_name: str):
                def kb_progress(current: int, total: int):
                    if progress_callback:
                        progress_callback(kb_name, current, total)

                return kb_progress

            count = self.index_kb(kb.name, make_kb_progress(kb.name))
            results[kb.name] = count

        return results

    def index_entry(self, entry: Entry, kb_name: str, file_path: Path) -> None:
        """Index a single entry."""
        data = self._entry_to_dict(entry, kb_name, file_path)
        self.db.upsert_entry(data)

    def remove_entry(self, entry_id: str, kb_name: str) -> bool:
        """Remove an entry from the index."""
        return self.db.delete_entry(entry_id, kb_name)

    def remove_kb(self, kb_name: str) -> None:
        """Remove a KB and all its entries from the index."""
        self.db.unregister_kb(kb_name)

    def get_index_stats(self) -> dict[str, Any]:
        """Get statistics about the index."""
        stats = {
            "kbs": {},
            "total_entries": 0,
            "total_tags": 0,
            "total_links": 0,
        }

        for kb in self.config.knowledge_bases:
            kb_stats = self.db.get_kb_stats(kb.name)
            if kb_stats:
                stats["kbs"][kb.name] = kb_stats
                stats["total_entries"] += kb_stats.get("actual_count", 0)

        # Get global counts
        global_counts = self.db.get_global_counts()
        stats["total_tags"] = global_counts["total_tags"]
        stats["total_links"] = global_counts["total_links"]

        return stats

    def check_health(self) -> dict[str, Any]:
        """
        Check index health and consistency.

        Returns dict with:
        - missing_files: entries in DB but file not found
        - unindexed_files: files not in DB
        - stale_entries: entries where file is newer than index
        """
        health = {
            "missing_files": [],
            "unindexed_files": [],
            "stale_entries": [],
        }

        for kb in self.config.knowledge_bases:
            if not kb.path.exists():
                continue

            repo = KBRepository(kb)

            # Get all indexed entries for this KB
            indexed = {}
            for row in self.db.get_entries_for_indexing(kb.name):
                indexed[row["id"]] = {
                    "file_path": row["file_path"],
                    "indexed_at": row["indexed_at"],
                }

            # Check each file
            seen_ids = set()
            for file_path in repo.list_files():
                try:
                    entry = repo._load_entry(file_path)
                    seen_ids.add(entry.id)

                    if entry.id not in indexed:
                        health["unindexed_files"].append(
                            {"kb": kb.name, "path": str(file_path), "id": entry.id}
                        )
                    else:
                        # Check if file is newer than index
                        indexed_at = indexed[entry.id]["indexed_at"]
                        if indexed_at:
                            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            index_time = datetime.fromisoformat(
                                indexed_at.replace("Z", "+00:00").replace("+00:00", "")
                            )
                            if file_mtime > index_time:
                                health["stale_entries"].append(
                                    {
                                        "kb": kb.name,
                                        "id": entry.id,
                                        "file_mtime": file_mtime.isoformat(),
                                        "indexed_at": indexed_at,
                                    }
                                )
                except Exception:
                    continue

            # Check for missing files
            for entry_id, info in indexed.items():
                if entry_id not in seen_ids:
                    health["missing_files"].append(
                        {"kb": kb.name, "id": entry_id, "path": info["file_path"]}
                    )

        return health

    def sync_incremental(self, kb_name: str | None = None) -> dict[str, int]:
        """
        Incremental sync: only update changed/new files.

        Returns dict with counts of added, updated, removed entries.
        """
        results = {"added": 0, "updated": 0, "removed": 0}

        kbs = [self.config.get_kb(kb_name)] if kb_name else self.config.knowledge_bases
        kbs = [kb for kb in kbs if kb and kb.path.exists()]

        for kb in kbs:
            repo = KBRepository(kb)

            # Ensure KB is registered
            self.db.register_kb(
                name=kb.name,
                kb_type=kb.kb_type,
                path=str(kb.path),
                description=kb.description,
            )

            # Get current index state
            indexed = {}
            for row in self.db.get_entries_for_indexing(kb.name):
                indexed[row["id"]] = {
                    "file_path": row["file_path"],
                    "indexed_at": row["indexed_at"],
                }

            seen_ids = set()

            # Check each file
            for entry, file_path in repo.list_entries():
                seen_ids.add(entry.id)

                if entry.id not in indexed:
                    # New entry
                    self.index_entry(entry, kb.name, file_path)
                    results["added"] += 1
                else:
                    # Check if updated
                    indexed_at = indexed[entry.id]["indexed_at"]
                    if indexed_at:
                        try:
                            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            index_time = datetime.fromisoformat(
                                indexed_at.replace("Z", "+00:00").replace("+00:00", "")
                            )
                            if file_mtime > index_time:
                                self.index_entry(entry, kb.name, file_path)
                                results["updated"] += 1
                        except Exception:
                            pass

            # Remove deleted entries
            for entry_id in indexed:
                if entry_id not in seen_ids:
                    self.remove_entry(entry_id, kb.name)
                    results["removed"] += 1

            # Update KB stats
            self.db.update_kb_indexed(kb.name, len(seen_ids))

        return results

    def index_with_attribution(
        self,
        kb_name: str,
        git_service: Any = None,
        since_commit: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> int:
        """
        Index a KB with git attribution.

        For each entry file:
        1. Parse and upsert entry (existing flow)
        2. git log --follow -> populate entry_version table
        3. Set entry.created_by = first commit author
        4. Set entry.modified_by = last commit author

        If since_commit is provided, only process changed files.

        Args:
            kb_name: KB to index
            git_service: GitService instance (or duck-typed equivalent)
            since_commit: Only process files changed since this commit
            progress_callback: Optional callback(current, total)

        Returns:
            Number of entries indexed
        """
        from ..services.git_service import GitService as GitServiceClass

        if git_service is None:
            git_service = GitServiceClass()

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise ValueError(f"KB '{kb_name}' not found in config")

        repo = KBRepository(kb_config)

        # Register KB in database
        self.db.register_kb(
            name=kb_name,
            kb_type=kb_config.kb_type,
            path=str(kb_config.path),
            description=kb_config.description,
        )

        # Determine which files to process
        kb_path = kb_config.path
        is_git = git_service.is_git_repo(kb_path)

        if since_commit and is_git:
            # Only changed files
            changed_files = git_service.get_changed_files(kb_path, since_commit=since_commit)
            files_to_process = set()
            for rel_path in changed_files:
                full_path = kb_path / rel_path
                if full_path.exists() and full_path.suffix == ".md":
                    files_to_process.add(full_path)
        else:
            files_to_process = None  # Process all

        indexed_count = 0
        error_count = 0

        for entry, file_path in repo.list_entries():
            if files_to_process is not None and file_path not in files_to_process:
                continue

            try:
                data = self._entry_to_dict(entry, kb_name, file_path)
                log_entries = []

                # Extract git attribution if available
                if is_git:
                    rel_path = str(file_path.relative_to(kb_path))
                    log_entries = git_service.get_file_log(kb_path, rel_path)

                    if log_entries:
                        # First commit = created_by, last commit = modified_by
                        data["created_by"] = log_entries[-1]["author_name"]
                        data["modified_by"] = log_entries[0]["author_name"]

                # Insert entry first (must exist before entry_version FK)
                self.db.upsert_entry(data)

                # Then populate entry_version table
                for i, log_entry in enumerate(log_entries):
                    change_type = "created" if i == len(log_entries) - 1 else "modified"
                    self.db.upsert_entry_version(
                        entry_id=entry.id,
                        kb_name=kb_name,
                        commit_hash=log_entry["hash"],
                        author_name=log_entry["author_name"],
                        author_email=log_entry["author_email"],
                        commit_date=log_entry["date"],
                        message=log_entry["message"],
                        change_type=change_type,
                    )
                indexed_count += 1

                if progress_callback:
                    progress_callback(indexed_count, 0)

            except Exception as e:
                logger.error("Failed to index %s: %s", file_path, e)
                error_count += 1

        # Update KB stats
        self.db.update_kb_indexed(kb_name, self.db.count_entries(kb_name))

        if error_count > 0:
            logger.warning("%d entries failed to index with attribution", error_count)

        return indexed_count


def create_index(config: PyriteConfig | None = None) -> IndexManager:
    """Create an IndexManager with default configuration."""
    config = config or load_config()
    db = PyriteDB(config.settings.index_path)
    return IndexManager(db, config)
