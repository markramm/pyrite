"""
Index Manager - Syncs File Storage with SQLite Index

Handles indexing entries from file-based KBs into the SQLite FTS database.
Supports incremental updates based on file modification times.
"""

import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import KBConfig, PyriteConfig, load_config
from ..models import Entry
from ..models.protocols import (
    PROTOCOL_COLUMN_KEYS,
    Assignable,
    Locatable,
    Prioritizable,
    Statusable,
    Temporal,
)
from .database import PyriteDB
from .repository import KBRepository

logger = logging.getLogger(__name__)

# Matches wikilinks: [[target]], [[kb:target]], [[target#heading]], [[target^block-id]], [[target|display]]
# Groups: (1) kb prefix, (2) target, (3) heading, (4) block-id, (5) display text
_WIKILINK_RE = re.compile(
    r"\[\[(?:([a-z0-9-]+):)?([^\]|#^]+?)(?:#([^\]|^]+?))?(?:\^([^\]|]+?))?(?:\|([^\]]+?))?\]\]"
)

# Matches transclusions: ![[target]], ![[target#heading]], ![[target^block-id]]
# Same groups as _WIKILINK_RE: (1) kb prefix, (2) target, (3) heading, (4) block-id, (5) display text
_TRANSCLUSION_RE = re.compile(
    r"!\[\[(?:([a-z0-9-]+):)?([^\]|#^]+?)(?:#([^\]|^]+?))?(?:\^([^\]|]+?))?(?:\|([^\]]+?))?\]\]"
)


def _parse_indexed_at(indexed_at: str) -> datetime:
    """Parse indexed_at timestamp string to a UTC-aware datetime.

    SQLite CURRENT_TIMESTAMP produces UTC strings like '2026-02-25 12:00:00'.
    Some values may have 'Z' or '+00:00' suffix. We normalize all to UTC-aware.
    If the value is the literal 'CURRENT_TIMESTAMP' (unresolved SQL default),
    treat it as "now".
    """
    if indexed_at == "CURRENT_TIMESTAMP":
        return datetime.now(UTC)
    cleaned = indexed_at.replace("Z", "+00:00")
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        # Naive datetime from SQLite — it's UTC
        dt = dt.replace(tzinfo=UTC)
    return dt


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
            "aliases": entry.aliases,
            "sources": [s.to_dict() for s in entry.sources],
            "links": [l.to_dict() for l in entry.links],
            "lifecycle": getattr(entry, "lifecycle", "active"),
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        }

        # Protocol-based field extraction (ADR-0017)
        # Temporal protocol: date, start_date, end_date, due_date
        if isinstance(entry, Temporal):
            data["date"] = entry.date
            data["start_date"] = entry.start_date
            data["end_date"] = entry.end_date
            data["due_date"] = entry.due_date
        elif hasattr(entry, "date"):
            data["date"] = entry.date

        # Locatable protocol: location, coordinates
        if isinstance(entry, Locatable):
            location = entry.location
            if isinstance(location, list):
                location = ", ".join(str(loc) for loc in location)
            data["location"] = location
            data["coordinates"] = entry.coordinates
        elif hasattr(entry, "location"):
            location = getattr(entry, "location", "")
            if isinstance(location, list):
                location = ", ".join(str(loc) for loc in location)
            data["location"] = location

        # Statusable protocol: status
        if isinstance(entry, Statusable):
            status = entry.status
            if hasattr(status, "value"):
                status = status.value
            elif isinstance(status, list):
                status = status[0] if status else None
            data["status"] = status
        elif hasattr(entry, "status"):
            status = getattr(entry, "status", "")
            if hasattr(status, "value"):
                status = status.value
            data["status"] = status

        # Assignable protocol: assignee, assigned_at
        if isinstance(entry, Assignable):
            data["assignee"] = entry.assignee
            data["assigned_at"] = entry.assigned_at
        elif hasattr(entry, "assignee"):
            data["assignee"] = getattr(entry, "assignee", "")

        # Prioritizable protocol: priority
        if isinstance(entry, Prioritizable):
            data["priority"] = entry.priority
        elif hasattr(entry, "priority"):
            data["priority"] = getattr(entry, "priority", "")

        # importance (promoted to base Entry)
        data["importance"] = entry.importance

        # For GenericEntry types: promote protocol fields from metadata to DB columns
        # This handles kb.yaml types that declare protocols: [temporal, assignable, ...]
        if hasattr(entry, "metadata") and entry.metadata:
            for key in PROTOCOL_COLUMN_KEYS:
                if key not in data and key in entry.metadata:
                    value = entry.metadata[key]
                    if key == "location" and isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    data[key] = value

        # Promote fips/state from metadata or entry attributes to DB columns
        # for geographic filtering (cross-KB FIPS queries)
        if hasattr(entry, "metadata") and entry.metadata:
            if "fips" not in data and "fips" in entry.metadata:
                data["fips"] = entry.metadata["fips"]
            if "state" not in data and "state" in entry.metadata:
                data["state"] = entry.metadata["state"]
        if "fips" not in data and hasattr(entry, "fips"):
            data["fips"] = getattr(entry, "fips", "")
        if "state" not in data and hasattr(entry, "state"):
            data["state"] = getattr(entry, "state", "")

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
            logger.warning(
                "Metadata extraction failed for %s, using fallback", entry.id, exc_info=True
            )
            # Fallback: just store the metadata dict
            if hasattr(entry, "metadata") and entry.metadata:
                data["metadata"] = entry.metadata

        # Extract body wikilinks as links with relation="wikilink"
        body = entry.body or ""
        if body:
            existing_targets = {l.get("target") for l in data["links"]}
            for match in _WIKILINK_RE.finditer(body):
                kb_prefix = match.group(1)  # Optional kb: prefix
                target = match.group(2).strip()
                heading = match.group(3)
                block_id = match.group(4)
                note = ""
                if heading:
                    note = f"#{heading}"
                elif block_id:
                    note = f"^{block_id}"
                if target and target != entry.id and target not in existing_targets:
                    data["links"].append(
                        {
                            "target": target,
                            "kb": kb_prefix or kb_name,
                            "relation": "wikilink",
                            "note": note,
                        }
                    )
                    existing_targets.add(target)

        # Extract references from frontmatter (cross-KB structured links)
        # Format: references: ["kb_name:entry_id", "entry_id", ...]
        refs = getattr(entry, "metadata", {})
        if isinstance(refs, dict):
            refs = refs.get("references", [])
        else:
            refs = []
        fm_refs = getattr(entry, "_raw_frontmatter", {}) or {}
        if not refs and isinstance(fm_refs, dict):
            refs = fm_refs.get("references", [])
        # Also check to_frontmatter output
        if not refs:
            try:
                fm = entry.to_frontmatter()
                refs = fm.get("references", [])
            except Exception:
                pass
        if isinstance(refs, list):
            existing_targets = {l.get("target") for l in data["links"]}
            for ref in refs:
                ref_str = str(ref).strip()
                if not ref_str:
                    continue
                if ":" in ref_str and not ref_str.startswith("http"):
                    ref_kb, ref_id = ref_str.split(":", 1)
                else:
                    ref_kb, ref_id = kb_name, ref_str
                if ref_id and ref_id != entry.id and ref_id not in existing_targets:
                    data["links"].append({
                        "target": ref_id,
                        "kb": ref_kb,
                        "relation": "references",
                        "note": "",
                    })
                    existing_targets.add(ref_id)

        # Extract transclusions as links with relation="transclusion"
        if body:
            for match in _TRANSCLUSION_RE.finditer(body):
                kb_prefix = match.group(1)
                target = match.group(2).strip()
                heading = match.group(3)
                block_id = match.group(4)
                note = ""
                if heading:
                    note = f"#{heading}"
                elif block_id:
                    note = f"^{block_id}"
                if target and target != entry.id and target not in existing_targets:
                    data["links"].append(
                        {
                            "target": target,
                            "kb": kb_prefix or kb_name,
                            "relation": "transclusion",
                            "note": note,
                        }
                    )
                    existing_targets.add(target)

        # Extract object-ref fields for entry_ref table
        refs = []
        try:
            kb_config = self.config.get_kb(kb_name)
            if kb_config and kb_config.kb_yaml_path.exists():
                schema = kb_config.kb_schema
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
            logger.debug("Schema not available for ref extraction: %s", entry.id)
        if refs:
            data["_refs"] = refs

        # Extract edge endpoints for edge_endpoint table
        edge_endpoints = []
        try:
            kb_config = self.config.get_kb(kb_name)
            if kb_config and kb_config.kb_yaml_path.exists():
                schema = kb_config.kb_schema
                entry_type_name = entry.entry_type
                type_schema = schema.types.get(entry_type_name)
                if type_schema and getattr(type_schema, "edge_type", False):
                    fm = entry.to_frontmatter()
                    for role, endpoint_spec in type_schema.endpoints.items():
                        value = fm.get(endpoint_spec.field)
                        if value and isinstance(value, str):
                            # Strip wikilink brackets if present: [[target]] -> target
                            endpoint_id = value.strip()
                            if endpoint_id.startswith("[[") and endpoint_id.endswith("]]"):
                                endpoint_id = endpoint_id[2:-2].strip()
                            if endpoint_id:
                                edge_endpoints.append(
                                    {
                                        "role": role,
                                        "field_name": endpoint_spec.field,
                                        "endpoint_id": endpoint_id,
                                        "endpoint_kb": kb_name,
                                        "edge_type": entry_type_name,
                                    }
                                )
        except Exception:
            logger.debug("Schema not available for edge endpoint extraction: %s", entry.id)
        if edge_endpoints:
            data["_edge_endpoints"] = edge_endpoints

        # Extract blocks for block-level references
        body = entry.body or ""
        if body:
            from ..utils.markdown_blocks import extract_blocks

            data["_blocks"] = extract_blocks(body)

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

        stats["type_counts"] = self.db.get_type_counts()

        return stats

    def _load_indexed_state(self, kb_name: str) -> dict[str, dict[str, str]]:
        """Load indexed entry state from DB for a KB.

        Returns dict mapping entry_id -> {"file_path": ..., "indexed_at": ...}.
        """
        indexed = {}
        for row in self.db.get_entries_for_indexing(kb_name):
            indexed[row["id"]] = {
                "file_path": row["file_path"],
                "indexed_at": row["indexed_at"],
            }
        return indexed

    @staticmethod
    def _is_stale(file_path: Path, indexed_at: str) -> bool:
        """Check whether a file is newer than its indexed_at timestamp."""
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
        index_time = _parse_indexed_at(indexed_at)
        return file_mtime > index_time

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
            "broken_links": 0,
        }

        for kb in self.config.knowledge_bases:
            if not kb.path.exists():
                continue

            repo = KBRepository(kb)
            indexed = self._load_indexed_state(kb.name)

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
                        indexed_at = indexed[entry.id]["indexed_at"]
                        if indexed_at and self._is_stale(file_path, indexed_at):
                            health["stale_entries"].append(
                                {
                                    "kb": kb.name,
                                    "id": entry.id,
                                    "file_mtime": datetime.fromtimestamp(
                                        file_path.stat().st_mtime, tz=UTC
                                    ).isoformat(),
                                    "indexed_at": indexed_at,
                                }
                            )
                except Exception:
                    logger.warning("Health check failed for entry %s", entry.id, exc_info=True)
                    continue

            # Check for missing files
            for entry_id, info in indexed.items():
                if entry_id not in seen_ids:
                    health["missing_files"].append(
                        {"kb": kb.name, "id": entry_id, "path": info["file_path"]}
                    )

        # Count broken links (targets that don't resolve to entries)
        broken_sql = """
            SELECT COUNT(*) as cnt FROM link l
            LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name
            WHERE e.id IS NULL
        """
        rows = self.db.execute_sql(broken_sql, {})
        if rows:
            health["broken_links"] = rows[0]["cnt"]

        return health

    def sync_incremental(
        self,
        kb_name: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, int]:
        """
        Incremental sync: only parse changed/new files, skip unchanged ones.

        Walks file paths first (no parsing), checks mtime-based staleness,
        and only parses files that are new or modified since last index.

        Args:
            kb_name: Sync specific KB (all if None)
            progress_callback: Optional callback(current, total) for progress updates

        Returns dict with counts of added, updated, removed entries.
        """
        results = {"added": 0, "updated": 0, "removed": 0}

        kbs = [self.config.get_kb(kb_name)] if kb_name else self.config.knowledge_bases
        kbs = [kb for kb in kbs if kb and kb.path.exists()]

        # Count total files across all KBs for progress (cheap: just path listing)
        total_files = 0
        if progress_callback:
            for kb in kbs:
                repo = KBRepository(kb)
                total_files += repo.count()

        processed = 0

        for kb in kbs:
            repo = KBRepository(kb)

            # Ensure KB is registered
            self.db.register_kb(
                name=kb.name,
                kb_type=kb.kb_type,
                path=str(kb.path),
                description=kb.description,
            )

            indexed = self._load_indexed_state(kb.name)

            # Build reverse map: file_path -> (entry_id, indexed_at)
            path_to_indexed: dict[str, tuple[str, str | None]] = {}
            for entry_id, info in indexed.items():
                fp = info.get("file_path")
                if fp:
                    path_to_indexed[fp] = (entry_id, info.get("indexed_at"))

            seen_ids: set[str] = set()

            # Walk all file paths without parsing
            for file_path in repo.list_all_files():
                fp_str = str(file_path)

                if fp_str in path_to_indexed:
                    # Known file — check staleness before parsing
                    entry_id, indexed_at = path_to_indexed[fp_str]
                    seen_ids.add(entry_id)

                    if indexed_at:
                        try:
                            if self._is_stale(file_path, indexed_at):
                                # Stale — parse and re-index
                                entry = repo.load_entry_from_file(file_path)
                                self.index_entry(entry, kb.name, file_path)
                                results["updated"] += 1
                        except Exception:
                            logger.warning(
                                "Stale check/re-index failed for %s", entry_id, exc_info=True
                            )
                else:
                    # Unknown file — parse to discover entry
                    try:
                        entry = repo.load_entry_from_file(file_path)
                        seen_ids.add(entry.id)
                        if entry.id in indexed:
                            # Entry exists but file path changed (rename)
                            self.index_entry(entry, kb.name, file_path)
                            results["updated"] += 1
                        else:
                            # Genuinely new entry
                            self.index_entry(entry, kb.name, file_path)
                            results["added"] += 1
                    except Exception:
                        logger.warning("Could not parse new file %s", file_path, exc_info=True)

                processed += 1
                if progress_callback and processed % 10 == 0:
                    progress_callback(processed, total_files)

            # Remove deleted entries
            for entry_id in indexed:
                if entry_id not in seen_ids:
                    self.remove_entry(entry_id, kb.name)
                    results["removed"] += 1

            # Update KB stats
            self.db.update_kb_indexed(kb.name, len(seen_ids))

        # Final progress callback
        if progress_callback:
            progress_callback(processed, total_files)

        return results

    def sync_kb(self, kb_config: KBConfig) -> dict[str, int]:
        """Sync a single KB given its config. Used by KBRegistryService for DB-only KBs."""
        results = {"added": 0, "updated": 0, "removed": 0}

        if not kb_config.path.exists():
            return results

        repo = KBRepository(kb_config)

        self.db.register_kb(
            name=kb_config.name,
            kb_type=kb_config.kb_type,
            path=str(kb_config.path),
            description=kb_config.description,
        )

        indexed = self._load_indexed_state(kb_config.name)
        seen_ids = set()

        for entry, file_path in repo.list_entries():
            seen_ids.add(entry.id)

            if entry.id not in indexed:
                self.index_entry(entry, kb_config.name, file_path)
                results["added"] += 1
            else:
                indexed_at = indexed[entry.id]["indexed_at"]
                if indexed_at:
                    try:
                        if self._is_stale(file_path, indexed_at):
                            self.index_entry(entry, kb_config.name, file_path)
                            results["updated"] += 1
                    except Exception:
                        logger.warning("Stale check failed for %s", entry.id, exc_info=True)

        for entry_id in indexed:
            if entry_id not in seen_ids:
                self.remove_entry(entry_id, kb_config.name)
                results["removed"] += 1

        self.db.update_kb_indexed(kb_config.name, len(seen_ids))
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
        if git_service is None:
            raise ValueError("git_service is required for index_with_attribution")

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
