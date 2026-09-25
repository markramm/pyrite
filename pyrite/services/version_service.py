"""
Version Service

Retrieves entry version history and content at specific git commits.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from ..config import PyriteConfig
from ..exceptions import InvalidGitRefError
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)

# A git object id, abbreviated or full: SHA-1 (40) or SHA-256 (64) hex, at
# least 4 characters (git's own minimum abbreviation). Nothing else -- no
# symbolic refs, no revision expressions, nothing git could read as an option.
_COMMIT_HASH_RE = re.compile(r"[0-9a-fA-F]{4,64}")


class VersionService:
    """Service for entry version history operations."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    def get_entry_versions(self, entry_id: str, kb_name: str, limit: int = 50) -> list[dict]:
        """Get version history for an entry."""
        return self.db.get_entry_versions(entry_id, kb_name, limit=limit)

    def get_entry_at_version(self, entry_id: str, kb_name: str, commit_hash: str) -> str | None:
        """Get entry content at a specific git commit.

        Raises:
            InvalidGitRefError: `commit_hash` is not a hex object id. Checked
                before any lookup or git call; this service is the only path
                from a caller-supplied hash to git.
        """
        import subprocess

        if not _COMMIT_HASH_RE.fullmatch(commit_hash):
            raise InvalidGitRefError("Invalid commit hash: expected a hex object id")

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
                ["git", "show", "--end-of-options", f"{commit_hash}:{rel_path}"],
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
