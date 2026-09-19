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

    # Keys that arrived under an explicit nested `metadata:` block. Only these
    # are written back nested; undeclared top-level keys are promoted instead,
    # so the same key can never be emitted twice (issue #149).
    _nested_metadata_keys: frozenset[str] = frozenset()

    @property
    def entry_type(self) -> str:
        return self._entry_type

    def to_frontmatter(self) -> dict[str, Any]:
        meta = self._base_frontmatter()
        if self.summary:
            meta["summary"] = self.summary
        # `_base_frontmatter` writes the whole `self.metadata` mapping as a
        # nested block; for an undeclared top-level key that duplicates the
        # promoted copy below and grows a `metadata:` block the source file
        # never had (#149). Keep only the keys that came from an explicit
        # `metadata:` block nested, and promote the rest.
        nested = {k: v for k, v in self.metadata.items() if k in self._nested_metadata_keys}
        if nested:
            meta["metadata"] = nested
        else:
            meta.pop("metadata", None)
        for key, value in self.metadata.items():
            if key in nested:
                continue
            if key not in meta:
                meta[key] = value
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "GenericEntry":
        kw = cls._base_kwargs(meta, body)

        # Collect unknown frontmatter keys into metadata
        explicit_metadata = meta.get("metadata", {}) or {}
        extra_metadata = {k: v for k, v in meta.items() if k not in _KNOWN_KEYS}
        # Merge: explicit metadata wins over inferred
        kw["metadata"] = {**extra_metadata, **explicit_metadata}
        # Remember which of those keys were nested in the source, so
        # to_frontmatter puts exactly them back nested and promotes the rest
        # (#149).
        kw["_nested_metadata_keys"] = frozenset(explicit_metadata)

        kw["lifecycle"] = meta.get("lifecycle", "active")
        kw["_entry_type"] = meta.get("type", "note")
        return cls(**kw)
