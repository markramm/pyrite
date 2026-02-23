"""Encyclopedia entry types."""

from dataclasses import dataclass, field
from typing import Any

from pyrite.models.base import parse_datetime, parse_links, parse_sources
from pyrite.models.core_types import NoteEntry
from pyrite.schema import Provenance, generate_entry_id

QUALITY_LEVELS = ("stub", "start", "C", "B", "GA", "FA")
REVIEW_STATUSES = ("draft", "under_review", "published")
PROTECTION_LEVELS = ("none", "semi", "full")


@dataclass
class ArticleEntry(NoteEntry):
    """An encyclopedia article.

    Published articles live in a shared namespace: articles/<slug>.md
    Drafts live per-author: drafts/<author>/<slug>.md
    """

    quality: str = "stub"  # stub, start, C, B, GA, FA
    review_status: str = "draft"  # draft, under_review, published
    protection_level: str = "none"  # none, semi, full
    categories: list[str] = field(default_factory=list)

    @property
    def entry_type(self) -> str:
        return "article"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "article"
        if self.quality != "stub":
            meta["quality"] = self.quality
        if self.review_status != "draft":
            meta["review_status"] = self.review_status
        if self.protection_level != "none":
            meta["protection_level"] = self.protection_level
        if self.categories:
            meta["categories"] = self.categories
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "ArticleEntry":
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
            quality=meta.get("quality", "stub"),
            review_status=meta.get("review_status", "draft"),
            protection_level=meta.get("protection_level", "none"),
            categories=meta.get("categories", []) or [],
        )


@dataclass
class TalkPageEntry(NoteEntry):
    """A discussion page associated with an article.

    Stored at: talk/<article-slug>.md
    """

    article_id: str = ""  # the article being discussed

    @property
    def entry_type(self) -> str:
        return "talk_page"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "talk_page"
        if self.article_id:
            meta["article_id"] = self.article_id
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TalkPageEntry":
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
            article_id=meta.get("article_id", ""),
        )
