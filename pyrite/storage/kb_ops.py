"""
KB registration and statistics.

Mixin class for KB management operations.
"""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import KB

if TYPE_CHECKING:
    from ..config import PyriteConfig

logger = logging.getLogger(__name__)


class KBOpsMixin:
    """KB registration, stats, and indexing metadata."""

    def register_kb(
        self,
        name: str,
        kb_type: str,
        path: str,
        description: str = "",
        source: str = "user",
        default_role: str | None = None,
    ) -> None:
        """Register a KB in the index."""
        type_str = kb_type.value if hasattr(kb_type, "value") else kb_type
        existing = self.session.get(KB, name)
        if existing:
            existing.kb_type = type_str
            existing.path = path
            existing.description = description
            existing.source = source
            if default_role is not None:
                existing.default_role = default_role
        else:
            kb = KB(
                name=name,
                kb_type=type_str,
                path=path,
                description=description,
                source=source,
                default_role=default_role,
            )
            self.session.add(kb)
        self.session.commit()

    def insert_new_kb(
        self,
        name: str,
        kb_type: str,
        path: str,
        description: str = "",
        source: str = "user",
        default_role: str | None = None,
    ) -> bool:
        """Register a KB only if no row has this name; never overwrite one.

        Returns False when the name is already registered. The primary key
        makes this atomic: of two concurrent inserts, one fails.
        `default_role` is written with the row, so a KB's access policy exists
        from the moment the KB does.
        """
        type_str = kb_type.value if hasattr(kb_type, "value") else kb_type
        if self.session.get(KB, name) is not None:
            return False
        self.session.add(
            KB(
                name=name,
                kb_type=type_str,
                path=path,
                description=description,
                source=source,
                default_role=default_role,
            )
        )
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            return False
        return True

    def merge_registered_kbs(self, config: "PyriteConfig") -> int:
        """Merge DB-registered KBs (from ``pyrite kb add``) into ``config``.

        Consolidates three near-identical copies of this raw-SQL merge that
        previously lived in cli/context.py, server/mcp_server.py, and
        server/api.py -- the latter two swallowed query failures with a
        bare ``except Exception: pass``, silently disappearing
        DB-registered KBs from the MCP/REST surfaces on any DB hiccup
        (fail-open-exception-sweep site #1, the dual-registry class again).

        Query failure (e.g. the ``kb`` table not existing yet on first
        run) is expected and non-fatal -- logged at warning so it's
        visible, but does not raise, since callers run this during
        construction and must not crash on a transient/first-run issue.

        Returns the number of KBs merged (0 on failure or none pending).
        """
        try:
            rows = self.session.execute(
                text(
                    "SELECT name, path, kb_type, description, default_role "
                    "FROM kb WHERE source = 'user'"
                )
            ).fetchall()
        except SQLAlchemyError:
            logger.warning(
                "Could not query DB-registered KBs to merge into config "
                "(kb table may not exist yet on first run)",
                exc_info=True,
            )
            return 0

        if not rows:
            return 0
        db_kbs = [
            {
                "name": r[0],
                "path": r[1],
                "kb_type": r[2],
                "description": r[3] or "",
                "default_role": r[4],
            }
            for r in rows
        ]
        return config.register_db_kbs(db_kbs)

    def update_kb_default_role(self, name: str, default_role: str | None) -> bool:
        """Update a KB's default_role. Returns True if KB was found."""
        kb = self.session.get(KB, name)
        if not kb:
            return False
        kb.default_role = default_role
        self.session.commit()
        return True

    def unregister_kb(self, name: str) -> None:
        """Remove a KB, all its entries, and every per-KB grant on it.

        The one place a KB is deleted -- registry removal (REST, MCP, CLI),
        repo unsubscribe and ephemeral expiry all come through here -- so the
        grants go here too. A `kb_permission` row outliving its KB is
        inherited by the next KB registered under the same name. Deleted
        even when the KB row is already gone, and in the same transaction.
        """
        kb = self.session.get(KB, name)
        if kb:
            self.session.delete(kb)
        self.session.execute(
            text("DELETE FROM kb_permission WHERE kb_name = :kb_name"), {"kb_name": name}
        )
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

    def get_type_counts(
        self, kb_name: str | None = None, kb_names: set[str] | list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Get entry counts grouped by entry_type, restricted to ``kb_names`` when given."""
        if kb_names is not None:
            from .backends.base_backend import kb_names_clause

            params: dict[str, Any] = {}
            scope = kb_names_clause("kb_name", kb_names, params)
            rows = self.session.execute(
                text(
                    f"SELECT entry_type, COUNT(*) as count FROM entry WHERE {scope} "
                    "GROUP BY entry_type ORDER BY count DESC"
                ),
                params,
            ).fetchall()
            return [dict(r._mapping) for r in rows]
        if kb_name:
            rows = self.session.execute(
                text(
                    "SELECT entry_type, COUNT(*) as count FROM entry WHERE kb_name = :kb GROUP BY entry_type ORDER BY count DESC"
                ),
                {"kb": kb_name},
            ).fetchall()
        else:
            rows = self.session.execute(
                text(
                    "SELECT entry_type, COUNT(*) as count FROM entry GROUP BY entry_type ORDER BY count DESC"
                ),
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
