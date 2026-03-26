"""
Export Service

KB export and git operations, including export-to-repo (clone, export, commit, push).
"""

import logging
import re
import tempfile
from pathlib import Path


def _yaml_quote(value: str) -> str:
    """Quote a YAML scalar value if it contains special characters."""
    if not value:
        return '""'
    # Values that need quoting: contains :, #, newline, leading/trailing spaces,
    # looks like a boolean/null, or starts with special chars
    needs_quoting = (
        ":" in value
        or "#" in value
        or "\n" in value
        or value != value.strip()
        or value.startswith(("{", "[", "'", '"', "&", "*", "!", "|", ">", "%", "@", "`"))
        or value.lower() in ("true", "false", "yes", "no", "null", "~", "on", "off")
        or re.match(r"^[\d.]+$", value)  # looks like a number
    )
    if needs_quoting:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return value

from ..config import PyriteConfig
from ..exceptions import KBNotFoundError, PyriteError
from ..storage.database import PyriteDB
from ..utils.sanitize import sanitize_filename

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

            # Format as markdown with frontmatter using proper YAML quoting
            fm_lines = ["---"]
            for key, val in frontmatter_fields.items():
                if isinstance(val, list):
                    fm_lines.append(f"{key}:")
                    for item in val:
                        fm_lines.append(f"  - {_yaml_quote(str(item))}")
                else:
                    fm_lines.append(f"{key}: {_yaml_quote(str(val))}")
            fm_lines.append("---")
            fm_lines.append("")

            content = "\n".join(fm_lines) + (body or "")

            file_path = type_dir / f"{sanitize_filename(entry_id)}.md"
            file_path.write_text(content, encoding="utf-8")
            files_created += 1

        return {
            "entries_exported": len(entries),
            "files_created": files_created,
        }

    def export_kb_to_repo(
        self,
        kb_name: str,
        repo_url: str,
        github_token: str | None = None,
        branch: str = "main",
        commit_message: str | None = None,
    ) -> dict:
        """Export a KB's entries into a target repo: clone, write entries, commit, push.

        Entries are written into a ``kb_name/`` subdirectory inside the target repo
        so that multiple KBs can coexist.

        Args:
            kb_name: KB to export
            repo_url: Remote repo URL to push to
            github_token: OAuth token (optional for public repos)
            branch: Branch to push to
            commit_message: Custom commit message

        Returns:
            Summary dict with entries_exported, commit_hash, etc.
        """
        from .git_service import GitService

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise KBNotFoundError(f"KB not found: {kb_name}")

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "repo"

            # Clone the target repo
            success, msg = GitService.clone(
                repo_url, clone_path, branch=branch, depth=None, token=github_token
            )
            if not success:
                return {"success": False, "error": f"Clone failed: {msg}"}

            # Export entries into kb_name/ subdirectory
            export_dir = clone_path / kb_name
            export_dir.mkdir(parents=True, exist_ok=True)
            result = self.export_kb_to_directory(kb_name, export_dir)

            if result["entries_exported"] == 0:
                return {"success": True, "entries_exported": 0, "message": "No entries to export"}

            # Commit
            if not commit_message:
                commit_message = f"Export KB '{kb_name}': {result['entries_exported']} entries"

            commit_ok, commit_result = GitService.commit(clone_path, commit_message)
            if not commit_ok:
                return {
                    "success": False,
                    "error": commit_result.get("error", "Commit failed"),
                }

            # Push
            push_ok, push_msg = GitService.push(
                clone_path, remote="origin", branch=branch, token=github_token
            )
            if not push_ok:
                return {"success": False, "error": push_msg}

            return {
                "success": True,
                **result,
                "commit_hash": commit_result.get("commit_hash", ""),
                "branch": branch,
                "message": f"Exported {result['entries_exported']} entries and pushed to {repo_url}",
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

    @staticmethod
    def export_collection_entries(
        entries: list,
        output_dir: Path,
        bundle_strategy=None,
        source_mode=None,
        title: str = "Exported Knowledge Base",
    ) -> dict:
        """Export a list of Entry objects as NotebookLM-ready markdown.

        Args:
            entries: List of Entry objects to export
            output_dir: Directory to write output files
            bundle_strategy: How to group entries into files (default: AUTO)
            source_mode: How to handle source visibility (default: PUBLIC)
            title: Title for the manifest document

        Returns:
            Summary dict with entries_exported, files_created
        """
        from ..renderers.notebooklm import (
            BundleStrategy,
            SourceMode,
            bundle_entries,
            generate_manifest,
        )

        if bundle_strategy is None:
            bundle_strategy = BundleStrategy.AUTO
        if source_mode is None:
            source_mode = SourceMode.PUBLIC

        if not entries:
            return {"entries_exported": 0, "files_created": 0}

        output_dir.mkdir(parents=True, exist_ok=True)

        # Bundle entries into files
        files = bundle_entries(entries, strategy=bundle_strategy, source_mode=source_mode)

        # Write bundled files
        for filename, content in files.items():
            (output_dir / filename).write_text(content, encoding="utf-8")

        # Generate and write manifest
        manifest = generate_manifest(entries, title=title)
        (output_dir / "_manifest.md").write_text(manifest, encoding="utf-8")

        return {
            "entries_exported": len(entries),
            "files_created": len(files),
        }

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
