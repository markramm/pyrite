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

    def update_kb_indexed(self, name: str, entry_count: int) -> None:
        """Update KB last indexed time and count."""
        kb = self.session.get(KB, name)
        if kb:
            kb.last_indexed = datetime.now(UTC).isoformat()
            kb.entry_count = entry_count
            self.session.commit()
