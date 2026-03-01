"""
KB Repository - File-based Storage

Handles reading and writing entries to/from markdown files.
Each KB is a directory of markdown files with YAML frontmatter.
"""

import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from ..config import KBConfig
from ..exceptions import KBReadOnlyError
from ..models import Entry, EventEntry
from ..models.collection import CollectionEntry
from ..models.core_types import entry_from_frontmatter
from ..migrations import get_migration_registry, load_plugin_migrations
from ..schema import CORE_TYPES
from ..utils.yaml import load_yaml_file

logger = logging.getLogger(__name__)


class KBRepository:
    """
    File-based repository for a single knowledge base.

    Handles:
    - Loading entries from markdown files
    - Saving entries to markdown files
    - Listing/iterating over entries
    - File path management
    """

    def __init__(self, kb_config: KBConfig):
        self.config = kb_config
        self.path = kb_config.path
        self.kb_type = kb_config.kb_type
        self.name = kb_config.name

    def _get_entry_class(self) -> type:
        """Get the default entry class for loading files."""
        # All files are loaded by parsing frontmatter and dispatching
        # to the correct type based on entry_type field
        return Entry

    def _load_entry(self, file_path: Path) -> Entry:
        """Load an entry from a file, dispatching to the correct type."""
        # Try to load with type-aware parsing
        try:
            # Read frontmatter to determine type
            text = file_path.read_text(encoding="utf-8")
            from pyrite.utils.yaml import load_yaml

            if text.startswith("---"):
                end = text.find("---", 3)
                if end > 0:
                    fm = load_yaml(text[3:end])
                    if fm and isinstance(fm, dict):
                        body = text[end + 3 :].strip()
                        fm = self._maybe_migrate(fm)
                        fm["body"] = body
                        fm["file_path"] = file_path
                        return entry_from_frontmatter(fm, body)

            # Fallback: try EventEntry.load for backward compat
            return EventEntry.load(file_path)
        except Exception:
            logger.warning("Entry load failed for %s, trying EventEntry fallback", file_path, exc_info=True)
            return EventEntry.load(file_path)

    def _maybe_migrate(self, fm: dict) -> dict:
        """Apply pending schema migrations to frontmatter if needed."""
        if not hasattr(self.config, "kb_yaml_path") or not self.config.kb_yaml_path.exists():
            return fm

        entry_type = fm.get("type", "")
        if not entry_type:
            return fm

        type_schema = self.config.kb_schema.get_type_schema(entry_type)
        if not type_schema or type_schema.version == 0:
            return fm

        entry_sv = int(fm.get("_schema_version", 0))
        if entry_sv >= type_schema.version:
            return fm

        load_plugin_migrations()
        registry = get_migration_registry()
        if not registry.has_migrations(entry_type):
            return fm

        try:
            fm = registry.apply(entry_type, fm, entry_sv, type_schema.version)
        except ValueError:
            logger.warning(
                "Migration failed for %s (v%d -> v%d)",
                entry_type, entry_sv, type_schema.version,
                exc_info=True,
            )

        return fm

    def _get_file_path(self, entry_id: str, subdir: str | None = None) -> Path:
        """Get file path for an entry."""
        if subdir:
            return self.path / subdir / f"{entry_id}.md"
        return self.path / f"{entry_id}.md"

    def _infer_subdir(self, entry: Entry) -> str | None:
        """Infer subdirectory for entries based on type."""
        entry_type = entry.entry_type
        # Check core types for subdirectory mapping
        if entry_type in CORE_TYPES:
            return CORE_TYPES[entry_type].get("subdirectory")
        # Plugin subtype: walk MRO to find the parent core type's subdirectory
        from ..models.core_types import ENTRY_TYPE_REGISTRY

        for core_name, core_cls in ENTRY_TYPE_REGISTRY.items():
            if isinstance(entry, core_cls) and core_name in CORE_TYPES:
                return CORE_TYPES[core_name].get("subdirectory")
        return None

    def exists(self, entry_id: str) -> bool:
        """Check if an entry exists."""
        # Check root
        if (self.path / f"{entry_id}.md").exists():
            return True

        # Check subdirectories
        for subdir in self.path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                if (subdir / f"{entry_id}.md").exists():
                    return True

        # Check for collection entries (collection-<folder_name>)
        if entry_id.startswith("collection-"):
            folder_name = entry_id[len("collection-"):]
            for subdir in self.path.rglob(folder_name):
                if subdir.is_dir() and (subdir / "__collection.yaml").exists():
                    return True

        return False

    def find_file(self, entry_id: str) -> Path | None:
        """Find the file path for an entry."""
        # Check root
        root_path = self.path / f"{entry_id}.md"
        if root_path.exists():
            return root_path

        # Check subdirectories
        for subdir in self.path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                file_path = subdir / f"{entry_id}.md"
                if file_path.exists():
                    return file_path

        # Check for collection entries (collection-<folder_name>)
        if entry_id.startswith("collection-"):
            folder_name = entry_id[len("collection-"):]
            for subdir in self.path.rglob(folder_name):
                if subdir.is_dir():
                    yaml_path = subdir / "__collection.yaml"
                    if yaml_path.exists():
                        return yaml_path

        return None

    def load(self, entry_id: str) -> Entry | None:
        """Load an entry by ID."""
        file_path = self.find_file(entry_id)
        if not file_path:
            return None

        try:
            entry = self._load_entry(file_path)
            entry.kb_name = self.name
            entry.file_path = file_path
            return entry
        except Exception as e:
            logger.warning("Could not load %s: %s", file_path, e)
            return None

    def save(self, entry: Entry, subdir: str | None = None) -> Path:
        """
        Save an entry to file.

        Args:
            entry: The entry to save
            subdir: Optional subdirectory (auto-inferred if not provided)

        Returns:
            Path to the saved file
        """
        if self.config.read_only:
            raise KBReadOnlyError(f"KB '{self.name}' is read-only")

        if subdir is None:
            subdir = self._infer_subdir(entry)

        file_path = self._get_file_path(entry.id, subdir)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Stamp current schema version on save
        if hasattr(self.config, "kb_yaml_path") and self.config.kb_yaml_path.exists():
            type_schema = self.config.kb_schema.get_type_schema(entry.entry_type)
            if type_schema and type_schema.version > 0:
                entry._schema_version = type_schema.version

        entry.updated_at = datetime.now(UTC)
        entry.save(file_path)
        entry.kb_name = self.name
        entry.file_path = file_path

        return file_path

    def delete(self, entry_id: str) -> bool:
        """Delete an entry file. Returns True if deleted."""
        if self.config.read_only:
            raise KBReadOnlyError(f"KB '{self.name}' is read-only")

        file_path = self.find_file(entry_id)
        if file_path and file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_files(self) -> Iterator[Path]:
        """Iterate over all markdown files in the KB."""
        for md_file in self.path.rglob("*.md"):
            # Skip hidden directories and files (check relative path only,
            # so a KB stored under e.g. ~/.pyrite/kbs/ is not skipped)
            rel = md_file.relative_to(self.path)
            if any(part.startswith(".") for part in rel.parts):
                continue
            # Skip templates
            if "template" in md_file.name.lower():
                continue
            yield md_file

    def list_entries(self) -> Iterator[tuple[Entry, Path]]:
        """Iterate over all entries in the KB."""
        for file_path in self.list_files():
            try:
                entry = self._load_entry(file_path)
                entry.kb_name = self.name
                entry.file_path = file_path
                yield entry, file_path
            except Exception as e:
                logger.warning("Could not parse %s: %s", file_path, e)
                continue

        # Discover __collection.yaml files
        for yaml_file in self.path.rglob("__collection.yaml"):
            if any(part.startswith(".") for part in yaml_file.parts):
                continue
            try:
                entry = self._load_collection(yaml_file)
                entry.kb_name = self.name
                entry.file_path = yaml_file
                yield entry, yaml_file
            except Exception as e:
                logger.warning("Could not parse collection %s: %s", yaml_file, e)
                continue

    def _load_collection(self, yaml_file: Path) -> CollectionEntry:
        """Load a CollectionEntry from a __collection.yaml file."""
        data = load_yaml_file(yaml_file)
        folder_path = str(yaml_file.parent.relative_to(self.path))
        return CollectionEntry.from_collection_yaml(data, folder_path)

    def count(self) -> int:
        """Count total entries in the KB."""
        md_count = sum(1 for _ in self.list_files())
        yaml_count = sum(
            1
            for f in self.path.rglob("__collection.yaml")
            if not any(part.startswith(".") for part in f.parts)
        )
        return md_count + yaml_count

    def search_files(self, query: str) -> Iterator[tuple[Entry, Path]]:
        """
        Simple file-based search (fallback when DB not indexed).

        For production use, prefer PyriteDB.search() which uses FTS5.
        """
        query_lower = query.lower()
        for file_path in self.list_files():
            try:
                content = file_path.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    entry = self._load_entry(file_path)
                    entry.kb_name = self.name
                    entry.file_path = file_path
                    yield entry, file_path
            except Exception:
                logger.warning("Skipping unreadable entry: %s", file_path, exc_info=True)
                continue

    def get_by_tag(self, tag: str) -> Iterator[Entry]:
        """Get entries with a specific tag."""
        for entry, _ in self.list_entries():
            if tag in entry.tags:
                yield entry

    def get_by_date_range(self, date_from: str, date_to: str) -> Iterator[Entry]:
        """Get events within a date range."""
        for entry, _ in self.list_entries():
            if isinstance(entry, EventEntry) and entry.date:
                if date_from <= entry.date <= date_to:
                    yield entry

    def validate_all(self) -> list[tuple[Path, list[str]]]:
        """Validate all entries. Returns list of (path, errors) for invalid entries."""
        invalid = []
        for entry, file_path in self.list_entries():
            errors = entry.validate()
            if errors:
                invalid.append((file_path, errors))
        return invalid


class MultiKBRepository:
    """
    Repository manager for multiple KBs.

    Provides unified access to multiple KBRepositories.
    """

    def __init__(self, kb_configs: list[KBConfig]):
        self.repos = {config.name: KBRepository(config) for config in kb_configs}

    def get_repo(self, kb_name: str) -> KBRepository | None:
        """Get repository for a specific KB."""
        return self.repos.get(kb_name)

    def load(self, entry_id: str, kb_name: str | None = None) -> Entry | None:
        """Load an entry, optionally searching across all KBs."""
        if kb_name:
            repo = self.get_repo(kb_name)
            return repo.load(entry_id) if repo else None

        # Search all KBs
        for repo in self.repos.values():
            entry = repo.load(entry_id)
            if entry:
                return entry
        return None

    def search(self, query: str, kb_name: str | None = None) -> Iterator[tuple[Entry, Path]]:
        """Search across KBs."""
        if kb_name:
            repo = self.get_repo(kb_name)
            if repo:
                yield from repo.search_files(query)
        else:
            for repo in self.repos.values():
                yield from repo.search_files(query)

    def list_all_entries(self) -> Iterator[tuple[str, Entry, Path]]:
        """List all entries across all KBs. Yields (kb_name, entry, path)."""
        for kb_name, repo in self.repos.items():
            for entry, path in repo.list_entries():
                yield kb_name, entry, path

    def count_all(self) -> dict:
        """Count entries in all KBs."""
        return {name: repo.count() for name, repo in self.repos.items()}
