"""Collection entry type — folder-backed collections (Phase 1)."""

from dataclasses import dataclass, field
from typing import Any

from ..schema import Provenance, generate_entry_id
from .base import Entry, parse_datetime, parse_links, parse_sources


@dataclass
class CollectionEntry(Entry):
    """A collection that groups entries, backed by a filesystem folder."""

    source_type: str = "folder"  # "folder" (Phase 1); "query" in Phase 2
    description: str = ""
    icon: str = ""
    view_config: dict = field(default_factory=lambda: {"default_view": "list"})
    entry_filter: dict = field(default_factory=dict)
    folder_path: str = ""  # Relative path within KB (for folder collections)

    @property
    def entry_type(self) -> str:
        return "collection"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.source_type != "folder":
            meta["source_type"] = self.source_type
        if self.description:
            meta["description"] = self.description
        if self.icon:
            meta["icon"] = self.icon
        if self.view_config and self.view_config != {"default_view": "list"}:
            meta["view_config"] = self.view_config
        if self.entry_filter:
            meta["entry_filter"] = self.entry_filter
        if self.folder_path:
            meta["folder_path"] = self.folder_path
        if self.summary:
            meta["summary"] = self.summary
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "CollectionEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            source_type=meta.get("source_type", "folder"),
            description=meta.get("description", ""),
            icon=meta.get("icon", ""),
            view_config=meta.get("view_config", {"default_view": "list"}) or {"default_view": "list"},
            entry_filter=meta.get("entry_filter", {}) or {},
            folder_path=meta.get("folder_path", ""),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )

    @classmethod
    def from_collection_yaml(cls, yaml_data: dict[str, Any], folder_path: str) -> "CollectionEntry":
        """Create a CollectionEntry from a parsed __collection.yaml file."""
        title = yaml_data.get("title", "")
        entry_id = yaml_data.get("id", "")
        if not entry_id:
            # Generate ID from folder name
            folder_name = folder_path.rstrip("/").split("/")[-1] if folder_path else ""
            entry_id = f"collection-{folder_name}" if folder_name else generate_entry_id(title)

        return cls(
            id=entry_id,
            title=title,
            body=yaml_data.get("body", ""),
            summary=yaml_data.get("summary", ""),
            source_type=yaml_data.get("source_type", "folder"),
            description=yaml_data.get("description", ""),
            icon=yaml_data.get("icon", ""),
            view_config=yaml_data.get("view_config", {"default_view": "list"}) or {"default_view": "list"},
            entry_filter=yaml_data.get("entry_filter", {}) or {},
            folder_path=folder_path,
            tags=yaml_data.get("tags", []) or [],
            sources=parse_sources(yaml_data.get("sources")),
            links=parse_links(yaml_data.get("links")),
            metadata=yaml_data.get("metadata", {}),
            created_at=parse_datetime(yaml_data.get("created_at")),
            updated_at=parse_datetime(yaml_data.get("updated_at")),
        )
