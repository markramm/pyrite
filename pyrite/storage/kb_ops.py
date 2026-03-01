"""
KB registration and statistics.

Mixin class for KB management operations.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from .models import KB


class KBOpsMixin:
    """KB registration, stats, and indexing metadata."""

    def register_kb(self, name: str, kb_type: str, path: str, description: str = "") -> None:
        """Register a KB in the index."""
        type_str = kb_type.value if hasattr(kb_type, "value") else kb_type
        existing = self.session.get(KB, name)
        if existing:
            existing.kb_type = type_str
            existing.path = path
            existing.description = description
        else:
            kb = KB(name=name, kb_type=type_str, path=path, description=description)
            self.session.add(kb)
        self.session.commit()

    def unregister_kb(self, name: str) -> None:
        """Remove a KB and all its entries from the index."""
        kb = self.session.get(KB, name)
        if kb:
            self.session.delete(kb)
            self.session.commit()

    def get_kb_stats(self, name: str) -> dict[str, Any] | None:
        """Get statistics for a KB."""
        row = self.session.execute(
            text("""
                SELECT k.*, COUNT(e.id) as actual_count
                FROM kb k
                LEFT JOIN entry e ON k.name = e.kb_name
                WHERE k.name = :name
                GROUP BY k.name
            """),
            {"name": name},
        ).fetchone()
        if row is None:
            return None
        return dict(row._mapping)

    def get_type_counts(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get entry counts grouped by entry_type."""
        if kb_name:
            rows = self.session.execute(
                text("SELECT entry_type, COUNT(*) as count FROM entry WHERE kb_name = :kb GROUP BY entry_type ORDER BY count DESC"),
                {"kb": kb_name},
            ).fetchall()
        else:
            rows = self.session.execute(
                text("SELECT entry_type, COUNT(*) as count FROM entry GROUP BY entry_type ORDER BY count DESC"),
            ).fetchall()
        return [dict(r._mapping) for r in rows]

    def link_kb_to_repo(self, kb_name: str, repo_id: int, repo_subpath: str) -> None:
        """Associate a KB with a repo."""
        kb = self.session.get(KB, kb_name)
        if kb:
            kb.repo_id = repo_id
            kb.repo_subpath = repo_subpath
            self.session.commit()

    def get_kbs_for_repo(self, repo_id: int) -> list[dict[str, Any]]:
        """Get KBs associated with a repo."""
        kbs = self.session.query(KB).filter_by(repo_id=repo_id).all()
        return [{"name": kb.name, "path": kb.path, "repo_subpath": kb.repo_subpath} for kb in kbs]

    def update_kb_indexed(self, name: str, entry_count: int) -> None:
        """Update KB last indexed time and count."""
        kb = self.session.get(KB, name)
        if kb:
            kb.last_indexed = datetime.now(UTC).isoformat()
            kb.entry_count = entry_count
            self.session.commit()
