"""Encyclopedia entry types."""

from dataclasses import dataclass, field
from typing import Any

from pyrite.models.core_types import NoteEntry

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
        meta["quality"] = self.quality
        meta["review_status"] = self.review_status
        meta["protection_level"] = self.protection_level
        if self.categories:
            meta["categories"] = self.categories
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "ArticleEntry":
        kw = cls._base_kwargs(meta, body)
        kw["quality"] = meta.get("quality", "stub")
        kw["review_status"] = meta.get("review_status", "draft")
        kw["protection_level"] = meta.get("protection_level", "none")
        kw["categories"] = meta.get("categories", []) or []
        return cls(**kw)


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
        kw = cls._base_kwargs(meta, body)
        kw["article_id"] = meta.get("article_id", "")
        return cls(**kw)
