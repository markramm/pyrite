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
from ..models.core_types import entry_from_frontmatter
from ..schema import CORE_TYPES

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
                        fm["body"] = body
                        fm["file_path"] = file_path
                        return entry_from_frontmatter(fm, body)

            # Fallback: try EventEntry.load for backward compat
            return EventEntry.load(file_path)
        except Exception:
            # Last resort: EventEntry.load
            return EventEntry.load(file_path)

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
            # Skip hidden directories and files
            if any(part.startswith(".") for part in md_file.parts):
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

    def count(self) -> int:
        """Count total entries in the KB."""
        return sum(1 for _ in self.list_files())

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
