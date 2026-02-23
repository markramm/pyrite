"""
Generic Entry Model

For custom types defined in kb.yaml that don't match a core type.
Custom fields live in self.metadata and round-trip through frontmatter.
"""

from dataclasses import dataclass
from typing import Any

from ..schema import Provenance, generate_entry_id
from .base import Entry, parse_datetime, parse_links, parse_sources

# Fields that are handled by Entry base or known frontmatter keys
_KNOWN_KEYS = {
    "id",
    "title",
    "type",
    "body",
    "summary",
    "tags",
    "sources",
    "links",
    "provenance",
    "metadata",
    "created_at",
    "updated_at",
}


@dataclass
class GenericEntry(Entry):
    """
    Flexible entry for kb.yaml-defined custom types.

    Custom fields live in self.metadata.
    Frontmatter round-trips all unknown keys through metadata.
    """

    _entry_type: str = "note"

    @property
    def entry_type(self) -> str:
        return self._entry_type

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.summary:
            meta["summary"] = self.summary
        # Promote metadata keys to top-level frontmatter
        for key, value in self.metadata.items():
            if key not in meta:
                meta[key] = value
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "GenericEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        # Collect unknown frontmatter keys into metadata
        explicit_metadata = meta.get("metadata", {})
        extra_metadata = {k: v for k, v in meta.items() if k not in _KNOWN_KEYS}
        # Merge: explicit metadata wins over inferred
        merged_metadata = {**extra_metadata, **explicit_metadata}

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=merged_metadata,
            _entry_type=meta.get("type", "note"),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
        )
