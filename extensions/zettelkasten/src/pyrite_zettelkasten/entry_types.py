"""Zettelkasten entry types."""

from dataclasses import dataclass, field
from typing import Any

from pyrite.models.core_types import NoteEntry

ZETTEL_TYPES = ("fleeting", "literature", "permanent", "hub")
MATURITY_LEVELS = ("seed", "sapling", "evergreen")
PROCESSING_STAGES = ("capture", "elaborate", "question", "review", "connect")


@dataclass
class ZettelEntry(NoteEntry):
    """Atomic knowledge note in the Zettelkasten tradition.

    Extends NoteEntry with zettel-specific metadata for the CEQRC workflow:
    Capture -> Elaborate -> Question -> Review -> Connect
    """

    zettel_type: str = "fleeting"  # fleeting, literature, permanent, hub
    maturity: str = "seed"  # seed, sapling, evergreen
    source_ref: str = ""  # reference to source material
    processing_stage: str = ""  # capture, elaborate, question, review, connect

    @property
    def entry_type(self) -> str:
        return "zettel"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "zettel"
        meta["zettel_type"] = self.zettel_type
        meta["maturity"] = self.maturity
        if self.source_ref:
            meta["source_ref"] = self.source_ref
        if self.processing_stage:
            meta["processing_stage"] = self.processing_stage
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "ZettelEntry":
        kw = cls._base_kwargs(meta, body)
        kw["zettel_type"] = meta.get("zettel_type", "fleeting")
        kw["maturity"] = meta.get("maturity", "seed")
        kw["source_ref"] = meta.get("source_ref", "")
        kw["processing_stage"] = meta.get("processing_stage", "")
        return cls(**kw)


@dataclass
class LiteratureNoteEntry(NoteEntry):
    """A note capturing ideas from a specific source work."""

    source_work: str = ""  # title/reference of the source
    author: str = ""
    page_refs: list[str] = field(default_factory=list)

    @property
    def entry_type(self) -> str:
        return "literature_note"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "literature_note"
        if self.source_work:
            meta["source_work"] = self.source_work
        if self.author:
            meta["author"] = self.author
        if self.page_refs:
            meta["page_refs"] = self.page_refs
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "LiteratureNoteEntry":
        kw = cls._base_kwargs(meta, body)
        kw["source_work"] = meta.get("source_work", "")
        kw["author"] = meta.get("author", "")
        kw["page_refs"] = meta.get("page_refs", []) or []
        return cls(**kw)
