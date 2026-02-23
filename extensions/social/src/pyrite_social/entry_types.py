"""Social KB entry types."""

from dataclasses import dataclass
from typing import Any

from pyrite.models.base import parse_datetime, parse_links, parse_sources
from pyrite.models.core_types import NoteEntry, PersonEntry
from pyrite.schema import Provenance, generate_entry_id

WRITEUP_TYPES = ("essay", "story", "review", "howto", "opinion")


@dataclass
class WriteupEntry(NoteEntry):
    """A user-authored writeup in a social knowledge base.

    Stored in folder-per-author layout: writeups/<author_id>/slug.md
    """

    author_id: str = ""
    writeup_type: str = "essay"  # essay, story, review, howto, opinion
    allow_voting: bool = True

    @property
    def entry_type(self) -> str:
        return "writeup"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "writeup"
        if self.author_id:
            meta["author_id"] = self.author_id
        if self.writeup_type != "essay":
            meta["writeup_type"] = self.writeup_type
        if not self.allow_voting:
            meta["allow_voting"] = self.allow_voting
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "WriteupEntry":
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
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
            author_id=meta.get("author_id", ""),
            writeup_type=meta.get("writeup_type", "essay"),
            allow_voting=meta.get("allow_voting", True),
        )


@dataclass
class UserProfileEntry(PersonEntry):
    """A user profile in a social knowledge base.

    Stored at: users/<user_id>.md
    """

    reputation: int = 0
    join_date: str = ""
    writeup_count: int = 0

    @property
    def entry_type(self) -> str:
        return "user_profile"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "user_profile"
        if self.reputation:
            meta["reputation"] = self.reputation
        if self.join_date:
            meta["join_date"] = self.join_date
        if self.writeup_count:
            meta["writeup_count"] = self.writeup_count
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "UserProfileEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        from pyrite.schema import ResearchStatus

        status_str = meta.get("research_status", "stub")
        try:
            research_status = ResearchStatus(status_str)
        except ValueError:
            research_status = ResearchStatus.STUB

        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            role=meta.get("role", ""),
            affiliations=meta.get("affiliations", []) or [],
            importance=int(meta.get("importance", 5)),
            research_status=research_status,
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
            reputation=int(meta.get("reputation", 0)),
            join_date=meta.get("join_date", ""),
            writeup_count=int(meta.get("writeup_count", 0)),
        )
