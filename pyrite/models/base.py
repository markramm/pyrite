"""
Base Entry Model

Abstract base for all KB entry types.
"""

import copy
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
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


# The value `importance` takes when frontmatter does not set it. Kept as a name
# so the write path can tell "unset" from "deliberately 5".
DEFAULT_IMPORTANCE = 5


# Base keys every class handles through _base_kwargs / _base_frontmatter even
# when it does not re-emit them (empty values are omitted on write).
#
# `body`, `file_path`, `kb_name` and `extra_frontmatter` are Entry attributes,
# never frontmatter. They are listed so that a loader which puts them into the
# meta dict it passes to capture_extra_frontmatter cannot have them recorded as
# undeclared frontmatter and written back into the file on the next save (#46).
_BASE_CONSUMED_KEYS = frozenset(
    {
        "body",
        "file_path",
        "kb_name",
        "extra_frontmatter",
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


def _default_valued_keys_absent_from(entry: "Entry", meta: dict[str, Any]) -> frozenset[str]:
    """Keys a pristine instance of ``entry``'s class writes, that ``meta`` lacks.

    Some fields are serialized even at their default value, because the default
    is a meaningful choice a user may have made (`importance: 5`, `rank: 0`).
    That is right for an entry built in memory, but on a load -> save round trip
    it invents keys the file never had, turning a one-field update into a
    frontmatter rewrite (#46).

    The set is computed by serializing a default-constructed instance of the
    same class: whatever it emits is an always-written key, and the ones absent
    from the source frontmatter are the ones to keep absent. Doing it
    empirically means a plugin type gets the behaviour without declaring
    anything, matching how ``capture_extra_frontmatter`` decides "unknown".
    """
    try:
        pristine = type(entry)(id=entry.id, title=entry.title)
        always_written = set(pristine.to_frontmatter())
    except Exception:  # a class needing more constructor args opts out
        return frozenset()
    return frozenset(k for k in always_written if k not in meta)


def capture_extra_frontmatter(entry: "Entry", meta: dict[str, Any]) -> None:
    """Record the top-level keys ``entry``'s class did not re-emit.

    Called by every load path after ``from_frontmatter``. "Unknown" is decided
    empirically -- a key is kept if serializing the freshly loaded entry does
    not produce it -- so no class has to list its own fields, and a plugin
    type gets the guarantee for free.
    """
    # Set before serializing: both influence what to_frontmatter emits, and
    # `emitted` below must reflect the decisions the write path will make.
    entry._absent_default_keys = _default_valued_keys_absent_from(entry, meta)
    # Keep the mapping as ruamel parsed it, for style on the way back out.
    entry._source_frontmatter = meta
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


def _plain(value: Any) -> Any:
    """Strip ruamel node types so two values can be compared by content."""
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _keep_sequence_style(old: Any, new: Any) -> Any:
    """Return ``new``, rendered in ``old``'s sequence style where that applies.

    A list whose contents changed still wants the brackets it had:
    `tags: [a, b]` edited to three tags should stay on one line rather than
    becoming a four-line block list.
    """
    if not isinstance(new, list) or isinstance(new, str):
        return new
    try:
        from ruamel.yaml.comments import CommentedSeq

        if isinstance(old, CommentedSeq) and old.fa.flow_style():
            seq = CommentedSeq(new)
            seq.fa.set_flow_style()
            return seq
    except Exception:  # style is a nicety; never fail a save for it
        pass
    return new


def _restyle_like_source(meta: dict[str, Any], source: Any) -> dict[str, Any]:
    """Re-emit ``meta`` in ``source``'s key order and YAML style.

    ``meta`` is a freshly built plain dict: correct in content, but it has lost
    the key order, quoting and flow/block style that ruamel preserved when the
    file was read. Writing it as-is turns a one-field update into a diff that
    touches every line, which is how the #46 frontmatter corruption stayed
    invisible in review.

    For each key ``source`` had and ``meta`` still has, the source node is
    reused when the value is unchanged (keeping `tags: [a, b]` inline and
    `"2026-07-03"` quoted) and replaced when it is not. Keys dropped from
    ``meta`` are dropped here too, and keys ``meta`` added are appended in its
    own order. With no source -- a newly created entry -- ``meta`` is returned
    untouched.
    """
    if not isinstance(source, Mapping):
        return meta

    try:
        restyled = copy.deepcopy(source)
    except Exception:  # a source we cannot copy is not worth failing a save over
        return meta

    for key in list(restyled.keys()):
        if key not in meta:
            del restyled[key]
        elif _plain(restyled[key]) != _plain(meta[key]):
            restyled[key] = _keep_sequence_style(restyled[key], meta[key])

    for key, value in meta.items():
        if key not in restyled:
            restyled[key] = value

    return restyled


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
    importance: int = DEFAULT_IMPORTANCE
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

    # Keys whose value equals their default and which this entry was loaded
    # WITHOUT. `importance: 5` and `rank: 0` are deliberately serialized even at
    # their defaults -- commit 7783335 fixed the data loss of dropping an
    # explicit `importance: 5` -- but that rule made a one-field update add
    # those lines to files that never had them (#46). So the rule now applies
    # to entries built in memory (the set is empty, everything is written),
    # while a load records which default-valued keys were absent so re-saving
    # does not invent them. Not a constructor argument: subclasses build kwargs
    # from _base_kwargs and would have to thread it through.
    _absent_default_keys: frozenset[str] = field(
        default=frozenset(), init=False, repr=False, compare=False
    )

    def _omit_default(self, key: str) -> bool:
        """True when ``key`` holds its default and the source file lacked it."""
        return key in self._absent_default_keys

    # The frontmatter mapping this entry was parsed from, as ruamel returned it
    # (a CommentedMap carrying key order, quoting and flow/block style). The
    # write path uses it to re-emit unchanged keys exactly as they were, so a
    # one-field update produces a one-line diff instead of reordering and
    # restyling the whole block (#46). Never read as data -- only as style.
    _source_frontmatter: Any = field(default=None, init=False, repr=False, compare=False)

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
        # An explicit importance is always written (commit 7783335); a default
        # one is written unless the file this entry came from had no such key.
        if self.importance != DEFAULT_IMPORTANCE or not self._omit_default("importance"):
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
        meta = _restyle_like_source(self.to_frontmatter(), self._source_frontmatter)
        yaml_front = dump_yaml(meta)
        # Exactly one trailing newline: the loader strips the body anyway, and a
        # body that already ended in newlines produced a blank last line that
        # failed the end-of-file hook on every freshly created entry.
        body = self.body.rstrip("\n")
        return f"---\n{yaml_front}\n---\n" + (f"\n{body}\n" if body else "")

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
