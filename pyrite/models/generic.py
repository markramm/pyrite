"""
Generic Entry Model

For custom types defined in kb.yaml that don't match a core type.
Custom fields live in self.metadata and round-trip through frontmatter.
"""

from dataclasses import dataclass
from typing import Any

from .base import Entry

# Fields that are handled by Entry base or known frontmatter keys
_KNOWN_KEYS = {
    "id",
    "title",
    "type",
    "body",
    "summary",
    "tags",
    "aliases",
    "sources",
    "links",
    "provenance",
    "metadata",
    "created_at",
    "updated_at",
    "_schema_version",
    "file_path",
    "importance",
    "lifecycle",
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
        kw = cls._base_kwargs(meta, body)

        # Collect unknown frontmatter keys into metadata
        explicit_metadata = meta.get("metadata", {})
        extra_metadata = {k: v for k, v in meta.items() if k not in _KNOWN_KEYS}
        # Merge: explicit metadata wins over inferred
        kw["metadata"] = {**extra_metadata, **explicit_metadata}

        kw["lifecycle"] = meta.get("lifecycle", "active")
        kw["_entry_type"] = meta.get("type", "note")
        return cls(**kw)
