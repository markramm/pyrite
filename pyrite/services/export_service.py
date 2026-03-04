"""
Export Service

KB export and git operations.
"""

import logging
from pathlib import Path

from ..config import PyriteConfig
from ..exceptions import KBNotFoundError, PyriteError
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class ExportService:
    """Service for KB export and git operations."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    def export_kb_to_directory(self, kb_name: str, target_dir: Path) -> dict:
        """Export all entries in a KB as markdown files to a directory.

        Args:
            kb_name: Name of the KB to export
            target_dir: Target directory for exported files

        Returns:
            Summary dict with entries_exported and files_created
        """
        import shutil

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")

        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy kb.yaml if it exists
        kb_yaml_src = kb_config.kb_yaml_path
        if kb_yaml_src.exists():
            shutil.copy2(kb_yaml_src, target_dir / "kb.yaml")

        # Get all entries from the KB
        entries = self.db.list_entries(kb_name=kb_name, limit=100000)

        files_created = 0
        for entry in entries:
            entry_type = entry.get("entry_type", "note")
            entry_id = entry.get("id", "unknown")
            title = entry.get("title", "")
            body = entry.get("body", "")

            # Organize by entry_type subdirectory
            type_dir = target_dir / entry_type
            type_dir.mkdir(parents=True, exist_ok=True)

            # Build YAML frontmatter
            frontmatter_fields = {
                "title": title,
                "type": entry_type,
            }
            if entry.get("date"):
                frontmatter_fields["date"] = entry["date"]
            if entry.get("status"):
                frontmatter_fields["status"] = entry["status"]
            if entry.get("tags"):
                frontmatter_fields["tags"] = entry["tags"]

            # Format as markdown with frontmatter
            fm_lines = ["---"]
            for key, val in frontmatter_fields.items():
                if isinstance(val, list):
                    fm_lines.append(f"{key}:")
                    for item in val:
                        fm_lines.append(f"  - {item}")
                else:
                    fm_lines.append(f"{key}: {val}")
            fm_lines.append("---")
            fm_lines.append("")

            content = "\n".join(fm_lines) + (body or "")

            file_path = type_dir / f"{entry_id}.md"
            file_path.write_text(content, encoding="utf-8")
            files_created += 1

        return {
            "entries_exported": len(entries),
            "files_created": files_created,
        }

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

        success, result = GitService.commit(kb.path, message, paths=paths, sign_off=sign_off)

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
