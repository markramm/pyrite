"""
SearchBackend protocol — the contract any index backend must satisfy.

Knowledge-index tables (entry, entry_fts, vec_entry, tag, entry_tag,
link, entry_ref, source, block) are managed exclusively through this
protocol.  App-state tables (kb, user, repo, etc.) stay in PyriteDB/ORM.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SearchBackend(Protocol):
    """Protocol for pluggable search/index backends."""

    # ── lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Release backend resources."""
        ...

    # ── entry CRUD ───────────────────────────────────────────────────

    def upsert_entry(self, entry_data: dict[str, Any]) -> None:
        """Insert or update an entry with all related data (tags, links, etc.)."""
        ...

    def delete_entry(self, entry_id: str, kb_name: str) -> bool:
        """Delete an entry and all related data. Returns True if deleted."""
        ...

    def get_entry(self, entry_id: str, kb_name: str) -> dict[str, Any] | None:
        """Get a single entry with tags, sources, and links."""
        ...

    def list_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List entries with pagination and optional filters."""
        ...

    def count_entries(
        self,
        kb_name: str | None = None,
        entry_type: str | None = None,
        tag: str | None = None,
    ) -> int:
        """Count entries matching filters."""
        ...

    def get_distinct_types(self, kb_name: str | None = None) -> list[str]:
        """Get distinct entry types."""
        ...

    def get_entries_for_indexing(self, kb_name: str) -> list[dict[str, Any]]:
        """Get entry id/file_path/indexed_at for incremental sync."""
        ...

    # ── full-text search ─────────────────────────────────────────────

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
        """Full-text search across entries."""
        ...

    def search_by_tag(
        self, tag: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by exact tag."""
        ...

    def search_by_date_range(
        self,
        date_from: str,
        date_to: str,
        kb_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search entries within a date range."""
        ...

    def search_by_tag_prefix(
        self, prefix: str, kb_name: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search entries by tag prefix (parent includes children)."""
        ...

    # ── semantic search (embeddings) ─────────────────────────────────

    def upsert_embedding(
        self, entry_id: str, kb_name: str, embedding: list[float]
    ) -> bool:
        """Store/update a vector embedding for an entry. Returns True on success."""
        ...

    def search_semantic(
        self,
        embedding: list[float],
        kb_name: str | None = None,
        limit: int = 20,
        max_distance: float = 1.3,
    ) -> list[dict[str, Any]]:
        """KNN search over stored embeddings."""
        ...

    def has_embeddings(self) -> bool:
        """Check if any embeddings exist."""
        ...

    def embedding_stats(self) -> dict[str, Any]:
        """Get embedding coverage statistics."""
        ...

    def get_embedded_rowids(self) -> set[int]:
        """Get set of rowids that already have embeddings."""
        ...

    def get_entries_for_embedding(
        self, kb_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Get entries with rowid for batch embedding."""
        ...

    def delete_embedding(self, entry_id: str, kb_name: str) -> None:
        """Delete embedding for an entry."""
        ...

    # ── graph (links) ────────────────────────────────────────────────

    def get_backlinks(
        self,
        entry_id: str,
        kb_name: str,
        limit: int = 0,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get entries that link TO this entry."""
        ...

    def get_outlinks(self, entry_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get entries this entry links TO."""
        ...

    def get_graph_data(
        self,
        center: str | None = None,
        center_kb: str | None = None,
        kb_name: str | None = None,
        entry_type: str | None = None,
        depth: int = 2,
        limit: int = 500,
    ) -> dict[str, Any]:
        """Multi-hop BFS graph traversal returning {nodes, edges}."""
        ...

    def get_most_linked(
        self, kb_name: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get entries with most incoming links."""
        ...

    def get_orphans(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get entries with no links (neither direction)."""
        ...

    # ── tags ─────────────────────────────────────────────────────────

    def get_all_tags(
        self, kb_name: str | None = None
    ) -> list[tuple[str, int]]:
        """Get all tags with counts."""
        ...

    def get_tags_as_dicts(
        self,
        kb_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get tags with counts as dicts."""
        ...

    # ── timeline ─────────────────────────────────────────────────────

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
        ...

    # ── object refs ──────────────────────────────────────────────────

    def get_refs_from(
        self, entry_id: str, kb_name: str
    ) -> list[dict[str, Any]]:
        """Get entries this entry references via object-ref fields."""
        ...

    def get_refs_to(
        self, entry_id: str, kb_name: str
    ) -> list[dict[str, Any]]:
        """Get entries that reference this entry."""
        ...

    # ── folder queries ───────────────────────────────────────────────

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
        ...

    def count_entries_in_folder(self, kb_name: str, folder_path: str) -> int:
        """Count entries in a folder."""
        ...

    # ── global counts ────────────────────────────────────────────────

    def get_global_counts(self) -> dict[str, int]:
        """Get global tag and link counts."""
        ...
