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
from typing import Any, ClassVar

from ..exceptions import FrontmatterError
from ..schema import Link, Provenance, Source
from ..utils.yaml import dump_yaml, load_yaml

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(UTC)


# Base keys every class handles through _base_kwargs / _base_frontmatter even
# when it does not re-emit them (empty values are omitted on write).
_BASE_CONSUMED_KEYS = frozenset(
    {
        "id",
        "title",
        "type",
        "summary",
        "tags",
        "aliases",
        "sources",
        "links",
        "provenance",
        "metadata",
        "importance",
        "lifecycle",
        "created_at",
        "updated_at",
        "_schema_version",
    }
)


def capture_extra_frontmatter(entry: "Entry", meta: dict[str, Any]) -> None:
    """Record the top-level keys ``entry``'s class did not re-emit.

    Called by every load path after ``from_frontmatter``. "Unknown" is decided
    empirically -- a key is kept if serializing the freshly loaded entry does
    not produce it -- so no class has to list its own fields, and a plugin
    type gets the guarantee for free.
    """
    try:
        emitted = entry.to_frontmatter()
    except Exception:  # a class that cannot serialize is not this helper's problem
        return
    extras = {
        k: v
        for k, v in meta.items()
        if k not in emitted and k not in _BASE_CONSUMED_KEYS and k not in entry.FRONTMATTER_ALIASES
    }
    if extras:
        entry.extra_frontmatter = extras


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
    importance: int = 5
    lifecycle: str = "active"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    # KB reference (set when loaded)
    kb_name: str = ""
    file_path: Path | None = None
    _schema_version: int = 0
    # Top-level frontmatter keys this class did not declare, captured at load
    # and written back at save, so a load -> save through a typed class never
    # deletes what it does not understand (`milestone:`, `github_issue:`, a
    # field a plugin added last week). Not indexed, not compared.
    extra_frontmatter: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    # Legacy frontmatter keys a class reads under another name (e.g. `participants`
    # -> `actors`). They are consumed, not unknown, so they are not preserved
    # as extras (which would write the value twice).
    FRONTMATTER_ALIASES: ClassVar[frozenset[str]] = frozenset()

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

    @staticmethod
    def _base_kwargs(meta: dict[str, Any], body: str) -> dict[str, Any]:
        """Extract common constructor kwargs from frontmatter.

        Subclass from_frontmatter methods should call this and extend with
        type-specific fields, eliminating boilerplate.
        """
        from ..schema import generate_entry_id
        from ..utils.parse import safe_int

        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))

        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None

        return {
            "id": entry_id,
            "title": meta.get("title", ""),
            "body": body,
            "summary": meta.get("summary", ""),
            "importance": safe_int(meta.get("importance"), 5),
            "tags": meta.get("tags", []) or [],
            "aliases": meta.get("aliases", []) or [],
            "sources": parse_sources(meta.get("sources")),
            "links": parse_links(meta.get("links")),
            "provenance": provenance,
            "metadata": meta.get("metadata", {}),
            "created_at": parse_datetime(meta.get("created_at")),
            "updated_at": parse_datetime(meta.get("updated_at")),
            "_schema_version": safe_int(meta.get("_schema_version"), 0),
        }

    def _base_frontmatter(self) -> dict[str, Any]:
        """Build common frontmatter fields.

        Starts from the undeclared keys captured at load, so declared fields
        set below (and in subclasses) always win over a stale extra.
        """
        meta: dict[str, Any] = dict(self.extra_frontmatter)
        meta.update(
            {
                "id": self.id,
                "title": self.title,
                "type": self.entry_type,
            }
        )

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
        meta["importance"] = self.importance
        if self.lifecycle != "active":
            meta["lifecycle"] = self.lifecycle
        if self.metadata:
            meta["metadata"] = self.metadata
        if self._schema_version > 0:
            meta["_schema_version"] = self._schema_version

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
            "lifecycle": self.lifecycle,
            "metadata": self.metadata,
        }

    def to_markdown(self) -> str:
        """Convert to markdown string with YAML frontmatter."""
        meta = self.to_frontmatter()
        yaml_front = dump_yaml(meta)
        return f"---\n{yaml_front}\n---\n\n{self.body}\n"

    @classmethod
    def from_markdown(cls, text: str) -> "Entry":
        """Parse from markdown string with YAML frontmatter.

        The opening `---` fence MUST be on line 1. If the file starts
        with anything else (body prose, a blank line, a BOM), the file is
        treated as having no frontmatter — even if a stray `---` divider
        appears later in the body. Pre-fix, ``re.split`` on
        ``^---\\s*$`` with ``MULTILINE`` would match body horizontal-rule
        dividers and feed body prose to the YAML loader, producing
        confusing ``ComposerError``/alias errors deep in ruamel
        (see Tier A bug r1030).
        """
        # Strip a UTF-8 BOM if present so files saved by Windows editors
        # still match the fence-at-line-1 rule.
        if text.startswith("﻿"):
            text = text[1:]

        # Require the fence at line 1. Anything else means no frontmatter
        # block, regardless of body content.
        if not text.startswith(("---\n", "---\r\n")):
            raise FrontmatterError("Invalid entry format: missing YAML frontmatter")

        # Drop the opening fence and split on the next `---` line.
        # maxsplit=1 here so any later `---` lines stay in the body.
        after_open = text.split("\n", 1)[1] if "\n" in text else ""
        close_parts = re.split(r"^---\s*$", after_open, flags=re.MULTILINE, maxsplit=1)
        if len(close_parts) < 2:
            raise FrontmatterError("Invalid entry format: missing YAML frontmatter")

        meta = load_yaml(close_parts[0])
        body = close_parts[1].strip()

        entry = cls.from_frontmatter(meta, body)
        # Restore lifecycle from frontmatter (base field, not in subclass constructors)
        if entry is not None:
            entry.lifecycle = meta.get("lifecycle", "active")
            capture_extra_frontmatter(entry, meta)
        return entry

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
        # Atomic replace: agents race on the same file (claim vs reset, claim
        # vs claim) and a plain write_text lets a concurrent load() read a
        # truncated file. Temp file in the same directory so the rename is
        # atomic on POSIX and Windows; a failed write leaves the old file intact.
        import os
        import tempfile

        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self.to_markdown())
            # mkstemp gives 0600; keep the existing file's mode, or what a
            # plain write would have produced under the current umask.
            try:
                mode = os.stat(path).st_mode & 0o777
            except FileNotFoundError:
                umask = os.umask(0)
                os.umask(umask)
                mode = 0o666 & ~umask
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
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
