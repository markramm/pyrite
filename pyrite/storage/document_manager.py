"""
Document Manager — Write-path coordination for KB entries.

Consolidates the repeated save-register-index pattern from KBService
into a single class, completing the ODM abstraction layer.
"""

import logging
from pathlib import Path

from ..config import KBConfig
from ..models import Entry
from .database import PyriteDB
from .index import IndexManager
from .repository import KBRepository

logger = logging.getLogger(__name__)


class DocumentManager:
    """Coordinates file storage and index updates for KB entries.

    Encapsulates the write-path pattern:
        KBRepository.save() → PyriteDB.register_kb() → IndexManager.index_entry()

    Read paths remain on PyriteDB / KBService directly.
    """

    def __init__(self, db: PyriteDB, index_mgr: IndexManager):
        self._db = db
        self._index_mgr = index_mgr

    def save_entry(self, entry: Entry, kb_name: str, kb_config: KBConfig) -> Path:
        """Save an entry to disk, register the KB, and index it.

        Args:
            entry: The entry to save.
            kb_name: Name of the knowledge base.
            kb_config: KB configuration (provides path, type, description).

        Returns:
            Path to the saved file.
        """
        repo = KBRepository(kb_config)
        file_path = repo.save(entry)

        self._db.register_kb(
            name=kb_name,
            kb_type=kb_config.kb_type,
            path=str(kb_config.path),
            description=kb_config.description,
        )

        self._index_mgr.index_entry(entry, kb_name, file_path)
        return file_path

    def delete_entry(self, entry_id: str, kb_name: str, kb_config: KBConfig) -> bool:
        """Delete an entry from disk and remove it from the index.

        Args:
            entry_id: ID of the entry to delete.
            kb_name: Name of the knowledge base.
            kb_config: KB configuration.

        Returns:
            True if the file was deleted, False if not found.
        """
        repo = KBRepository(kb_config)
        file_deleted = repo.delete(entry_id)
        self._db.delete_entry(entry_id, kb_name)
        return file_deleted

    def index_entry(self, entry: Entry, kb_name: str, file_path: Path) -> None:
        """Index an entry without writing to disk (re-index from existing file).

        Args:
            entry: The entry to index.
            kb_name: Name of the knowledge base.
            file_path: Path to the existing file on disk.
        """
        self._index_mgr.index_entry(entry, kb_name, file_path)
