"""
Search, graph, analytics, and timeline queries.

Mixin class for read-only query operations.
Delegates knowledge-index queries to ``self._backend``.
Settings methods use ORM directly (app-state, not in SearchBackend).
"""

from datetime import UTC, datetime
from typing import Any

from .models import Setting


class QueryMixin:
    """Search, graph traversal, analytics, and timeline queries — delegates to backend."""

    # =========================================================================
    # Full-text and filtered search
    # =========================================================================

    def search(
        self,
        query: str,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Full-text search across entries using FTS5."""
        return self._backend.search(
            query=query, kb_name=kb_name, entry_type=entry_type,
            tags=tags, date_from=date_from, date_to=date_to,
            limit=limit, offset=offset,
        )

    def search_by_tag(
        self, tag: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by tag."""
        return self._backend.search_by_tag(tag=tag, kb_name=kb_name, limit=limit)

    def search_by_date_range(
        self,
        date_from: str,
        date_to: str,
        kb_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search events within a date range."""
        return self._backend.search_by_date_range(
            date_from=date_from, date_to=date_to, kb_name=kb_name, limit=limit
        )

    # =========================================================================
    # Graph queries (links)
    # =========================================================================

    def get_backlinks(
        self,
        entry_id: str,
        kb_name: str,
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get entries that link TO this entry."""
        return self._backend.get_backlinks(
            entry_id=entry_id, kb_name=kb_name, limit=limit, offset=offset
        )

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that this entry links TO."""
        return self._backend.get_outlinks(entry_id=entry_id, kb_name=kb_name)

    def get_related(self, entry_id: str, kb_name: str, depth: int = 1) -> list[dict[str, Any]]:
        """Get related entries (both directions) up to N hops."""
        backlinks = self._backend.get_backlinks(entry_id, kb_name)
        outlinks = self._backend.get_outlinks(entry_id, kb_name)

        related = []
        seen = set()
        for link in backlinks + outlinks:
            key = (link.get("id"), link.get("kb_name"))
            if key not in seen and key != (entry_id, kb_name):
                seen.add(key)
                related.append(link)
        return related

    def get_graph_data(
        self,
        center: str | None = None,
        center_kb: str | None = None,
        kb_name: str | None = None,
        entry_type: str | None = None,
        depth: int = 2,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Multi-hop BFS graph traversal returning nodes and edges."""
        return self._backend.get_graph_data(
            center=center, center_kb=center_kb,
            kb_name=kb_name, entry_type=entry_type,
            depth=depth, limit=limit,
        )

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_all_tags(self, kb_name: str | None = None) -> list[tuple[str, int]]:
        """Get all tags with counts."""
        return self._backend.get_all_tags(kb_name=kb_name)

    def get_most_linked(self, kb_name: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Get entries with most incoming links (most referenced)."""
        return self._backend.get_most_linked(kb_name=kb_name, limit=limit)

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get entries with no links (neither incoming nor outgoing)."""
        return self._backend.get_orphans(kb_name=kb_name)

    def get_timeline(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        min_importance: int = 1,
        kb_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get timeline events ordered by date."""
        return self._backend.get_timeline(
            date_from=date_from, date_to=date_to,
            min_importance=min_importance, kb_name=kb_name,
            limit=limit, offset=offset,
        )

    def get_global_counts(self) -> dict[str, int]:
        """Get global tag and link counts."""
        return self._backend.get_global_counts()

    def get_tags_as_dicts(
        self,
        kb_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get tags with counts as dicts, optionally filtered by KB and prefix."""
        return self._backend.get_tags_as_dicts(
            kb_name=kb_name, limit=limit, offset=offset, prefix=prefix
        )

    # =========================================================================
    # Object Refs
    # =========================================================================

    def get_refs_from(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries this entry references via object-ref fields."""
        return self._backend.get_refs_from(entry_id=entry_id, kb_name=kb_name)

    def get_refs_to(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries that reference this entry via object-ref fields."""
        return self._backend.get_refs_to(entry_id=entry_id, kb_name=kb_name)

    # =========================================================================
    # Settings (app-state — stays in ORM, not in SearchBackend)
    # =========================================================================

    def get_setting(self, key: str) -> str | None:
        """Get a setting value by key."""
        setting = self.session.query(Setting).filter_by(key=key).first()
        return setting.value if setting else None

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value (upsert)."""
        now = datetime.now(UTC).isoformat()
        existing = self.session.query(Setting).filter_by(key=key).first()
        if existing:
            existing.value = value
            existing.updated_at = now
        else:
            setting = Setting(key=key, value=value, updated_at=now)
            self.session.add(setting)
        self.session.commit()

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings as a dict."""
        settings = self.session.query(Setting).all()
        return {s.key: s.value for s in settings}

    def delete_setting(self, key: str) -> bool:
        """Delete a setting. Returns True if deleted."""
        count = self.session.query(Setting).filter_by(key=key).delete()
        self.session.commit()
        return count > 0

    # =========================================================================
    # Tag hierarchy (computed from backend data)
    # =========================================================================

    def get_tag_tree(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Build hierarchical tag tree from /-separated tags."""
        flat_tags = self._backend.get_all_tags(kb_name)

        root_children: list[dict[str, Any]] = []
        node_map: dict[str, dict[str, Any]] = {}

        for tag_name, count in sorted(flat_tags, key=lambda t: t[0]):
            parts = tag_name.split("/")
            for i, part in enumerate(parts):
                full_path = "/".join(parts[: i + 1])
                if full_path not in node_map:
                    node: dict[str, Any] = {
                        "name": part,
                        "full_path": full_path,
                        "count": 0,
                        "children": [],
                    }
                    node_map[full_path] = node
                    if i == 0:
                        root_children.append(node)
                    else:
                        parent_path = "/".join(parts[:i])
                        node_map[parent_path]["children"].append(node)
            if tag_name in node_map:
                node_map[tag_name]["count"] = count

        return root_children

    # =========================================================================
    # Folder queries (for collections)
    # =========================================================================

    def list_entries_in_folder(
        self,
        kb_name: str,
        folder_path: str,
        sort_by: str = "title",
        sort_order: str = "asc",
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List entries whose file_path is within the given folder."""
        return self._backend.list_entries_in_folder(
            kb_name=kb_name, folder_path=folder_path,
            sort_by=sort_by, sort_order=sort_order,
            limit=limit, offset=offset,
        )

    def count_entries_in_folder(self, kb_name: str, folder_path: str) -> int:
        """Count entries whose file_path is within the given folder."""
        return self._backend.count_entries_in_folder(kb_name=kb_name, folder_path=folder_path)

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by tag prefix (parent tag includes children)."""
        return self._backend.search_by_tag_prefix(prefix=prefix, kb_name=kb_name, limit=limit)
