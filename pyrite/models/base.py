"""
Base Entry Model

Abstract base for all KB entry types.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from ..schema import Link, Provenance, Source
from ..utils.yaml import dump_yaml, load_yaml


def _utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


@dataclass
class Entry(ABC):
    """
    Abstract base class for all KB entries.

    All entries share:
    - ID and title
    - Body content
    - Tags and links
    - Sources and provenance
    - Timestamps
    - Metadata dict for extension fields
    """

    id: str
    title: str
    body: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    provenance: Provenance | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    # KB reference (set when loaded)
    kb_name: str = ""
    file_path: Path | None = None

    @property
    @abstractmethod
    def entry_type(self) -> str:
        """Return the entry type identifier."""
        pass

    @abstractmethod
    def to_frontmatter(self) -> dict[str, Any]:
        """Convert to YAML frontmatter dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "Entry":
        """Create from parsed frontmatter and body."""
        pass

    def _base_frontmatter(self) -> dict[str, Any]:
        """Build common frontmatter fields."""
        meta: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "type": self.entry_type,
        }

        if self.tags:
            meta["tags"] = self.tags
        if self.aliases:
            meta["aliases"] = self.aliases
        if self.sources:
            meta["sources"] = [s.to_dict() for s in self.sources]
        if self.links:
            meta["links"] = [l.to_dict() for l in self.links]
        if self.provenance:
            prov = self.provenance.to_dict()
            if prov:
                meta["provenance"] = prov
        if self.metadata:
            meta["metadata"] = self.metadata

        return meta

    def to_db_dict(self, kb_name: str, file_path: str) -> dict[str, Any]:
        """Serialize for DB. Subclasses override to add type-specific fields."""
        return {
            "id": self.id,
            "kb_name": kb_name,
            "entry_type": self.entry_type,
            "title": self.title,
            "body": self.body,
            "summary": self.summary,
            "file_path": file_path,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Convert to markdown string with YAML frontmatter."""
        meta = self.to_frontmatter()
        yaml_front = dump_yaml(meta)
        return f"---\n{yaml_front}\n---\n\n{self.body}\n"

    @classmethod
    def from_markdown(cls, text: str) -> "Entry":
        """Parse from markdown string with YAML frontmatter."""
        parts = re.split(r"^---\s*$", text, flags=re.MULTILINE, maxsplit=2)
        if len(parts) < 3:
            raise ValueError("Invalid entry format: missing YAML frontmatter")

        meta = load_yaml(parts[1])
        body = parts[2].strip()

        return cls.from_frontmatter(meta, body)

    @classmethod
    def load(cls, path: Path) -> "Entry":
        """Load entry from file."""
        text = path.read_text(encoding="utf-8")
        entry = cls.from_markdown(text)
        entry.file_path = path
        return entry

    def save(self, path: Path | None = None) -> Path:
        """Save entry to file."""
        if path is None:
            path = self.file_path
        if path is None:
            raise ValueError("No path specified and no file_path set")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_markdown(), encoding="utf-8")
        self.file_path = path
        return path

    def add_link(self, target: str, relation: str, note: str = "", kb: str = "") -> None:
        """Add a link to another entry."""
        self.links.append(Link(target=target, relation=relation, note=note, kb=kb))

    def add_source(self, title: str, url: str, **kwargs) -> None:
        """Add a source reference."""
        self.sources.append(Source(title=title, url=url, **kwargs))

    def validate(self) -> list[str]:
        """Validate entry. Returns list of errors."""
        errors = []
        if not self.id:
            errors.append("Entry must have an ID")
        if not self.title:
            errors.append("Entry must have a title")
        return errors

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r}, title={self.title!r})"


def parse_datetime(s: Any) -> datetime:
    """Parse datetime from various formats."""
    if isinstance(s, datetime):
        return s
    if not s:
        return _utcnow()
    try:
        # Try ISO format
        if isinstance(s, str):
            s = s.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
    except Exception:
        logger.warning("Failed to parse datetime: %s", s, exc_info=True)
    return _utcnow()


def parse_sources(sources_data: Any) -> list[Source]:
    """Parse sources from various formats."""
    if not sources_data:
        return []
    if isinstance(sources_data, list):
        return [
            Source.from_dict(s) if isinstance(s, dict) else Source(title=str(s), url="")
            for s in sources_data
        ]
    return []


def parse_links(links_data: Any) -> list[Link]:
    """Parse links from various formats."""
    if not links_data:
        return []
    if isinstance(links_data, list):
        return [
            Link.from_dict(l) if isinstance(l, dict) else Link(target=str(l), relation="related")
            for l in links_data
        ]
    return []
